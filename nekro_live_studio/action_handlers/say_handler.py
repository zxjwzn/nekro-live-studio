import asyncio
from typing import cast

from ..clients.vits_simple_api.client import vits_simple_api_client
from ..clients.vtuber_studio.plugin import plugin
from ..schemas.actions import Action, Say
from ..services.controller_manager import controller_manager
from ..services.websocket_manager import manager
from ..utils.logger import logger
from .base import ActionHandler


class SayHandler(ActionHandler):
    """处理 'say' 动作的具体策略"""

    async def handle(
        self,
        action: Action,
        tts_start_event: asyncio.Event | None = None,
    ):
        tts_lock = asyncio.Lock()
        say_action = cast(Say, action)
        is_say_with_tts = bool(say_action.data.tts_text)

        # 如果有TTS任务，并且当前任务不是那个TTS任务，则等待TTS开始信号
        if tts_start_event and not is_say_with_tts:
            logger.debug(f"动作 {action.type} 等待 TTS 开始...")
            await tts_start_event.wait()

        if is_say_with_tts:
            async with tts_lock:
                mouth_sync_controller = controller_manager.get_controller_by_name(
                    "MouthSyncController",
                )
                loudness_queue: asyncio.Queue[float | None] = asyncio.Queue()
                mouth_sync_task = None
                if mouth_sync_controller:
                    mouth_sync_task = asyncio.create_task(
                        mouth_sync_controller.execute(loudness_queue),
                    )

                start_event = asyncio.Event()
                finished_event = asyncio.Event()

                # 第一个获取锁的 say 动作将负责触发全局事件
                is_first_tts_runner = tts_start_event and not tts_start_event.is_set()

                # 在后台播放音频, 传递的是局部事件
                speak_task = asyncio.create_task(
                    vits_simple_api_client.speak(
                        text=say_action.data.tts_text,
                        started_event=start_event,
                        finished_event=finished_event,
                        volume=say_action.data.volume,
                        loudness_queue=loudness_queue,
                    ),
                )

                # 等待音频开始（或在开始前就失败）
                start_wait_task = asyncio.create_task(start_event.wait())
                finished_wait_task = asyncio.create_task(finished_event.wait())

                done, pending = await asyncio.wait(
                    {start_wait_task, finished_wait_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()
                # 等待被取消任务的收尾，防止未等待警告
                await asyncio.gather(*pending, return_exceptions=True)

                # 如果任务在开始前就失败了, 中止动作
                if finished_event.is_set() and not start_event.is_set():
                    logger.error("TTS 播放任务在开始前就已失败, 中止 'say' 动作.")
                    await speak_task  # 等待任务完成以获取可能的异常信息
                    return

                # 音频已开始, 如果是第一个, 则触发全局事件并暂停空闲动画
                if is_first_tts_runner and tts_start_event:
                    tts_start_event.set()

                logger.debug("音频已开始播放, 开始显示字幕...")
                await manager.broadcast_to_path(
                    "/ws/subtitles",
                    say_action.model_dump_json(),
                )

                # 等待音频播放完成
                await finished_event.wait()
                logger.debug("音频播放完毕, 发送完成消息.")
                await manager.broadcast_to_path("/ws/subtitles", '{"type": "finished"}')
                await speak_task  # 确保后台任务最终完成

                if mouth_sync_task:
                    await mouth_sync_task
        else:
            # 如果没有 tts_text，则只广播字幕
            await manager.broadcast_to_path(
                "/ws/subtitles",
                say_action.model_dump_json(),
            )
