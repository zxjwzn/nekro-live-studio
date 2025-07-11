import asyncio
import re
import subprocess
from typing import AsyncIterator, List, Optional, TypeVar

from ..configs.config import config
from ..utils.logger import logger

T = TypeVar("T")


async def atee(iterable: AsyncIterator[T], n: int = 2) -> List[AsyncIterator[T]]:
    """将一个异步迭代器 tee 分为多个独立的异步迭代器"""
    queues = [asyncio.Queue() for _ in range(n)]

    async def forward():
        try:
            async for item in iterable:
                for q in queues:
                    await q.put(item)
        finally:
            for q in queues:
                await q.put(None)  # Sentinel value to signal end of iteration

    asyncio.create_task(forward())

    async def gen(q: asyncio.Queue):
        while True:
            item = await q.get()
            if item is None:
                break
            yield item

    return [gen(q) for q in queues]


async def _analyze_loudness_stream(audio_stream: AsyncIterator[bytes], loudness_queue: asyncio.Queue):
    """
    使用 ffmpeg 分析音频流的响度 (LUFS), 并将结果放入队列.
    """
    args = [
        config.FFMPEG.FFMPEG_CMD,
        "-hide_banner",
        "-nostats",
        "-i",
        "pipe:0",
        "-af",
        "ebur128",
        "-f",
        "null",
        "-",
    ]
    process = await asyncio.create_subprocess_exec(
        *args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not process.stdin or not process.stderr:
        logger.error("响度分析进程未能初始化IO流")
        return

    lufs_pattern = re.compile(r"M:\s*(-?\d+\.?\d*)")

    async def read_stderr():
        """读取并解析 ffmpeg 的 stderr 输出."""
        if not process.stderr:
            return
        while not process.stderr.at_eof():
            line_bytes = await process.stderr.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", "ignore").strip()
            match = lufs_pattern.search(line)
            if match:
                try:
                    lufs = float(match.group(1))
                    await loudness_queue.put(lufs)
                except (ValueError, IndexError):
                    pass

    stderr_reader_task = asyncio.create_task(read_stderr())

    try:
        async for chunk in audio_stream:
            if process.stdin.is_closing():
                break
            try:
                process.stdin.write(chunk)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                logger.warning("Loudness analysis ffmpeg process closed pipe.")
                break
    finally:
        if not process.stdin.is_closing():
            process.stdin.close()
            await process.stdin.wait_closed()
        await process.wait()
        await stderr_reader_task


async def play_audio_stream_with_ffplay(
    audio_stream: AsyncIterator[bytes],
    started_event: asyncio.Event | None = None,
    finished_event: asyncio.Event | None = None,
    volume: float | None = None,
    loudness_queue: asyncio.Queue[Optional[float]] | None = None,
) -> bool:
    """
    使用 ffplay 播放音频流, 并可选择同时进行响度分析.
    """
    analysis_task = None
    if loudness_queue:
        play_stream, analysis_stream = await atee(audio_stream, 2)
        analysis_task = asyncio.create_task(_analyze_loudness_stream(analysis_stream, loudness_queue))
    else:
        play_stream = audio_stream

    try:
        args = [
            config.FFMPEG.FFPLAY_CMD,
            "-autoexit",
            "-nodisp",
            "-i",
            "pipe:0",
        ]
        if volume is not None:
            # ffplay音量是0-100的整数
            args.extend(["-volume", str(int(min(max(volume, 0.0), 1.0) * 100))])

        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if not process.stdin:
            logger.error("ffplay 进程未能初始化标准输入")
            if analysis_task and not analysis_task.done():
                analysis_task.cancel()
            return False

        set_started = False
        async for chunk in play_stream:
            if process.stdin.is_closing():
                break

            if not set_started and started_event:
                started_event.set()
                set_started = True

            try:
                process.stdin.write(chunk)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                logger.warning("ffplay 进程已关闭，无法继续写入音频流")
                break
            except Exception as e:
                logger.error(f"写入 ffplay 进程时发生错误: {e}")
                break

        if not process.stdin.is_closing():
            process.stdin.close()
            await process.stdin.wait_closed()

        await process.wait()

        if process.returncode != 0:
            stderr_output = ""
            if process.stderr:
                stderr_output_bytes = await process.stderr.read()
                stderr_output = stderr_output_bytes.decode("utf-8", errors="ignore").strip()
            if stderr_output:
                logger.error(f"ffplay 进程错误: {stderr_output}")
            return False

    except FileNotFoundError:
        logger.error(f"`{config.FFMPEG.FFPLAY_CMD}` 未找到，请确保已安装 ffmpeg 并将其添加至系统 PATH 或在配置中设置正确的路径")
        return False
    except Exception as e:
        logger.error(f"播放音频流时发生未知错误: {e}")
        return False
    finally:
        if analysis_task:
            await analysis_task
            if loudness_queue:
                await loudness_queue.put(None)  # 发送结束信号

        if finished_event:
            finished_event.set()

    return True
