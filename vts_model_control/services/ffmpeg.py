import asyncio
import json
import queue
import subprocess
import threading
from typing import AsyncIterator, Optional

from utils.logger import logger


async def play_audio_stream_with_ffplay(
    audio_stream: AsyncIterator[bytes],
    started_event: asyncio.Event | None = None,
    finished_event: asyncio.Event | None = None,
    volume: float | None = None,
) -> bool:
    """
    使用 ffplay 播放音频流，同时进行响度分析
    """
    
    try:
        # ffplay 参数
        args = [
            "ffplay",
            "-autoexit",
            "-nodisp",
            "-i",
            "pipe:0",
        ]
        if volume is not None:
            args.extend(["-volume", str(int(min(volume, 1.0) * 100))])

        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        set_started = False
        async for chunk in audio_stream:
            if process.stdin is None:
                break
                
            if not set_started and started_event:
                started_event.set()
                set_started = True

            try:
                # 写入到 ffplay
                process.stdin.write(chunk)
                await process.stdin.drain()
    
            except (BrokenPipeError, ConnectionResetError):
                logger.warning("ffplay 进程已关闭，无法继续写入音频流")
                break
            except Exception as e:
                logger.error(f"写入进程时发生错误: {e}")

        if process.stdin:
            process.stdin.close()
            await process.stdin.wait_closed()

        await process.wait()

        if process.returncode != 0:
            stderr_output = ""
            if process.stderr:
                stderr_output_bytes = await process.stderr.read()
                stderr_output = (
                    stderr_output_bytes.decode("utf-8", errors="ignore").strip()
                )
            if stderr_output:
                logger.error(f"ffplay 进程错误: {stderr_output}")
            return False

    except FileNotFoundError:
        logger.error("`ffplay` 未找到，请确保已安装 ffmpeg 并将其添加至系统 PATH")
        return False
    except Exception as e:
        logger.error(f"播放音频流时发生未知错误: {e}")
        return False
    finally:
        if finished_event:
            finished_event.set()
            
    return True