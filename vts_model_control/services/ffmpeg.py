import asyncio
import subprocess
from typing import AsyncIterator, cast

from controllers.lip_sync_controller import LipSyncController
from services.controller_manager import controller_manager
from utils.logger import logger


async def play_audio_stream_with_ffplay(
    audio_stream: AsyncIterator[bytes],
    started_event: asyncio.Event | None = None,
    finished_event: asyncio.Event | None = None,
    volume: float | None = None,
) -> bool:
    """
    使用 ffplay 播放音频流, 并通过 LipSyncController 同步嘴型
    """
    lip_sync_controller = cast(LipSyncController, controller_manager.get_controller("LipSyncController"))
    if not lip_sync_controller.config.ENABLED:
        logger.info("口型同步已禁用，仅播放音频")

    try:
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

            # 并行处理音频播放和口型同步
            tasks = [
                asyncio.create_task(lip_sync_controller.process_chunk(chunk)),
            ]
            try:
                process.stdin.write(chunk)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                logger.warning("ffplay 进程已关闭，无法继续写入音频流")
                # 不再向口型同步器发送数据，但允许完成当前任务
            except Exception as e:
                logger.error(f"写入 ffplay 进程时发生错误: {e}")

            # 等待口型同步任务完成，但不因其失败而中断播放
            await asyncio.gather(*tasks, return_exceptions=True)

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
        # 确保嘴巴最终闭合，并触发完成事件
        await lip_sync_controller.stop()
        if finished_event:
            finished_event.set()
    return True
