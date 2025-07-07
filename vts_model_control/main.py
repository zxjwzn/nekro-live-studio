import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from clients.live.bilibili_live import bilibili_live_client
from clients.vits_simple_api.client import vits_simple_api_client
from clients.vtuber_studio.plugin import plugin
from controllers.blink_controller import BlinkController
from controllers.body_swing_controller import BodySwingController
from controllers.breathing_controller import BreathingController
from controllers.mouth_expression_controller import MouthExpressionController
from controllers.mouth_sync import MouthSyncController
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from schemas.actions import (
    Animation,
    Execute,
    Expression,
    ListPreformAnimation,
    PlayPreformAnimation,
    ResponseMessage,
    Say,
    SoundPlay,
)
from services.action_scheduler import action_scheduler
from services.animation_player import animation_player
from services.audio_manager import audio_manager
from services.controller_manager import controller_manager
from services.subtitle_broadcaster import subtitle_broadcaster
from services.tweener import tweener
from services.websocket_manager import manager
from starlette.staticfiles import StaticFiles
from utils.logger import logger

from configs.config import config, reload_config, save_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("应用启动中...")
    # 连接 VTS
    logger.info(f"正在连接到 VTube Studio, 地址: {config.PLUGIN.VTS_ENDPOINT} 请在VTube Studio中点击认证")
    if not await plugin.connect_and_authenticate(config.PLUGIN.AUTHENTICATION_TOKEN):
        logger.error("连接 VTS 失败, 请检查 VTube Studio 是否已开启并加载API插件")
        sys.exit(1)
    if plugin.client.authentication_token:
        config.PLUGIN.AUTHENTICATION_TOKEN = plugin.client.authentication_token
        save_config()
    # 启动 Tweener
    tweener.start(plugin)

    controller_manager.register_controller(BlinkController())
    controller_manager.register_controller(BodySwingController())
    controller_manager.register_controller(BreathingController())
    controller_manager.register_controller(MouthExpressionController())
    controller_manager.register_controller(MouthSyncController())
    
    asyncio.create_task(controller_manager.start_all_idle())
    asyncio.create_task(bilibili_live_client.start())

    yield

    # Shutdown
    logger.info("应用关闭中...")
    save_config()
    await controller_manager.stop_all_idle()
    tweener.release_all()
    await tweener.stop()
    await plugin.disconnect()
    logger.info("应用已关闭")


app = FastAPI(lifespan=lifespan)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="data/resources"), name="static")


@app.get("/")
async def read_root():
    return {"message": "VTS Model Control API is running"}


@app.websocket("/ws/danmaku")
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
        manager.disconnect(websocket, path)
        logger.info(f"客户端 {client_host}:{client_port} 已从 {path} 断开")


@app.websocket("/ws/subtitles")
async def websocket_subtitles_endpoint(websocket: WebSocket):
    """处理字幕广播的WebSocket端点"""
    await subtitle_broadcaster.connect(websocket)
    client_host = websocket.client.host if websocket.client else "unknown"
    client_port = websocket.client.port if websocket.client else "unknown"
    logger.info(f"客户端 {client_host}:{client_port} 已连接到 /ws/subtitles")
    try:
        while True:
            # 保持连接开放以接收广播
            await websocket.receive_text()
    except WebSocketDisconnect:
        subtitle_broadcaster.disconnect(websocket)
        logger.info(f"客户端 {client_host}:{client_port} 已从 /ws/subtitles 断开")


@app.websocket("/ws/animate_control")
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
            try:
                if action_type == "say":
                    action = Say.model_validate(data)
                    logger.info(f"收到 Say action，已添加到队列: {action}")
                    action_scheduler.add_action(action)
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="说话动作已添加",
                        ).model_dump(),
                    )
                elif action_type == "animation":
                    action = Animation.model_validate(data)
                    logger.info(f"收到 Animation action，已添加到队列: {action}")
                    completion_time = action_scheduler.add_action(action)
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="动画动作已添加",
                            data={"estimated_completion_time": completion_time},
                        ).model_dump(),
                    )
                elif action_type == "expression":
                    action = Expression.model_validate(data)
                    logger.info("收到 Expression action")

                    completion_time = action_scheduler.add_action(action)
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="表情动作已添加",
                            data={"estimated_completion_time": completion_time},
                        ).model_dump(),
                    )
                elif action_type == "execute":
                    action = Execute.model_validate(data)
                    logger.info(f"收到 Execute action: {action}")
                    # 将耗时任务放入后台执行，避免阻塞WebSocket循环
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="动作队列已开始执行",
                        ).model_dump(),
                    )
                    await action_scheduler.execute_queue(loop=action.data.loop)
                elif action_type == "sound_play":
                    action = SoundPlay.model_validate(data)
                    logger.info("收到 SoundPlay action")
                    completion_time = action_scheduler.add_action(action)
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="音效动作已添加",
                            data={"estimated_completion_time": completion_time},
                        ).model_dump(),
                    )
                elif action_type == "list_preformed_animations":
                    _ = ListPreformAnimation.model_validate(data)
                    logger.info("收到 ListPreformAnimation action")
                    animations_list = animation_player.list_preformed_animations()
                    await websocket.send_json(
                        ResponseMessage(
                            status="success",
                            message="动画模板列表已获取",
                            data={
                                "type": "list_preformed_animations",
                                "animations": [
                                    anim.model_dump() for anim in animations_list
                                ],
                            },
                        ).model_dump(),
                    )
                elif action_type == "play_preformed_animation":
                    action = PlayPreformAnimation.model_validate(data)
                    logger.info(f"收到 PlayPreformAnimation action: {action.data.name}")
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
                                data={"type": "get_expressions", "expressions": expressions},
                            ).model_dump(),
                        )
                    except Exception as e:
                        logger.error(f"获取表情列表时发生错误: {e}")
                        await websocket.send_json({"status": "error", "message": f"获取表情列表失败: {e!s}"})
                elif action_type == "get_sounds":
                    try:
                        logger.info("收到 get_sounds action, 获取音效列表及其描述...")
                        sounds_with_descriptions = audio_manager.get_sounds_with_descriptions()

                        await websocket.send_json(
                            ResponseMessage(
                                status="success",
                                message="音效列表已获取",
                                data={"type": "get_sounds", "sounds": sounds_with_descriptions},
                            ).model_dump(),
                        )
                        logger.info("音效列表及描述已成功发送。")
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
            except ValidationError as e:
                logger.error(f"Action 数据校验失败: {e}, raw_data: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, path)
        logger.info(f"客户端 {client_host}:{client_port} 已从 {path} 断开")


if __name__ == "__main__":
    logger.info(f"API服务器将在 http://{config.API.HOST}:{config.API.PORT} 上启动")
    uvicorn.run(
        "main:app",
        host=config.API.HOST,
        port=config.API.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
