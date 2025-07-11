from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from ..clients.vtuber_studio.plugin import plugin
from ..schemas.actions import (
    Animation,
    Execute,
    Expression,
    ListPreformAnimation,
    PlayPreformAnimation,
    ResponseMessage,
    Say,
    SoundPlay,
)
from ..services.action_scheduler import action_scheduler
from ..services.animation_player import animation_player
from ..services.audio_manager import audio_manager
from ..services.websocket_manager import manager
from ..utils.logger import logger

router = APIRouter()


@router.get("/")
async def read_root():
    return {"message": "VTS Model Control API is running"}


@router.websocket("/ws/danmaku")
async def websocket_danmaku_endpoint(websocket: WebSocket):
    """
    处理B站弹幕的WebSocket端点.
    """
    path = "/ws/danmaku"
    await manager.connect(websocket, path)
    client_host = websocket.client.host if websocket.client else "unknown"
    client_port = websocket.client.port if websocket.client else "unknown"
    logger.info(f"客户端 {client_host}:{client_port} 已连接到 {path}")
    try:
        while True:
            # 等待客户端消息, 但在这里我们主要用于保持连接
            # 服务端到客户端的消息由BilibiliLiveClient广播
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, path)
        logger.info(f"客户端 {client_host}:{client_port} 已从 {path} 断开")


@router.websocket("/ws/subtitles")
async def websocket_subtitles_endpoint(websocket: WebSocket):
    """处理字幕广播的WebSocket端点"""
    path = "/ws/subtitles"
    await manager.connect(websocket, path)
    client_host = websocket.client.host if websocket.client else "unknown"
    client_port = websocket.client.port if websocket.client else "unknown"
    logger.debug(f"客户端 {client_host}:{client_port} 已连接到 /ws/subtitles")
    try:
        while True:
            # 保持连接开放以接收广播
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, path)
        logger.debug(f"客户端 {client_host}:{client_port} 已从 /ws/subtitles 断开")


@router.websocket("/ws/animate_control")
async def websocket_animate_control_endpoint(websocket: WebSocket):
    """
    处理动画控制的WebSocket端点.
    """
    path = "/ws/animate_control"
    await manager.connect(websocket, path)
    client_host = websocket.client.host if websocket.client else "unknown"
    client_port = websocket.client.port if websocket.client else "unknown"
    logger.info(f"客户端 {client_host}:{client_port} 已连接到 {path}")
    try:
        while True:
            data = await websocket.receive_json()
            action_type = data.get("type")

            # 将可由 ActionScheduler 处理的动作类型分组
            scheduled_actions = {
                "say": (Say, "说话动作已添加"),
                "animation": (Animation, "动画动作已添加"),
                "expression": (Expression, "表情动作已添加"),
                "sound_play": (SoundPlay, "音效动作已添加"),
            }

            try:
                if action_type in scheduled_actions:
                    model, success_message = scheduled_actions[action_type]
                    action = model.model_validate(data)
                    logger.debug(f"收到 {action.type} action，已添加到队列")

                    completion_time = action_scheduler.add_action(action)

                    # 仅部分动作返回预计完成时间
                    response_data = {"estimated_completion_time": completion_time} if action_type != "say" else None
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message=success_message,
                            data=response_data,
                        ).model_dump(),
                    )

                elif action_type == "execute":
                    action = Execute.model_validate(data)
                    logger.debug(f"收到 Execute action: {action}")
                    # 将耗时任务放入后台执行，避免阻塞WebSocket循环
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="动作队列已开始执行",
                        ).model_dump(),
                    )
                    await action_scheduler.execute_queue(loop=action.data.loop)
                elif action_type == "list_preformed_animations":
                    _ = ListPreformAnimation.model_validate(data)
                    logger.debug("收到 ListPreformAnimation action")
                    animations_list = animation_player.list_preformed_animations()
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="动画模板列表已获取",
                            data={
                                "type": "list_preformed_animations",
                                "animations": [anim.model_dump() for anim in animations_list],
                            },
                        ).model_dump(),
                    )
                elif action_type == "play_preformed_animation":
                    action = PlayPreformAnimation.model_validate(data)
                    logger.debug(f"收到 PlayPreformAnimation action: {action.data.name}")
                    completion_time = await animation_player.add_preformed_animation(
                        name=action.data.name,
                        params=action.data.params,
                        delay=action.data.delay,
                    )
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="动画模板播放任务已启动",
                            data={"estimated_completion_time": completion_time},
                        ).model_dump(),
                    )
                elif action_type == "get_expressions":
                    try:
                        # 返回所有表情列表
                        expressions = await plugin.get_expressions()
                        await websocket.send_json(
                            ResponseMessage(
                                status="success",
                                message="表情列表已获取",
                                data={
                                    "type": "get_expressions",
                                    "expressions": expressions,
                                },
                            ).model_dump(),
                        )
                    except Exception as e:
                        logger.exception("获取表情列表时发生错误")
                        await websocket.send_json({"status": "error", "message": f"获取表情列表失败: {e!s}"})
                elif action_type == "get_sounds":
                    try:
                        logger.debug("收到 get_sounds action, 获取音效列表及其描述...")
                        sounds_with_descriptions = audio_manager.get_sounds_with_descriptions()

                        await websocket.send_json(
                            ResponseMessage(
                                status="success",
                                message="音效列表已获取",
                                data={
                                    "type": "get_sounds",
                                    "sounds": sounds_with_descriptions,
                                },
                            ).model_dump(),
                        )
                        logger.debug("音效列表及描述已成功发送。")
                    except Exception as e:
                        logger.error(f"获取音效列表时发生错误: {e}", exc_info=True)
                        await websocket.send_json({"status": "error", "message": f"获取音效列表失败: {e!s}"})
                else:
                    logger.warning(f"未知的 action 类型: {action_type}")
                    await websocket.send_json(
                        ResponseMessage(
                            status="error",
                            message=f"未知的 action 类型: {action_type}",
                        ).model_dump(),
                    )
            except ValidationError:
                logger.exception(f"Action 数据校验失败, raw_data: {data}")

    except WebSocketDisconnect:
        await manager.disconnect(websocket, path)
        logger.debug(f"客户端 {client_host}:{client_port} 已从 {path} 断开")
