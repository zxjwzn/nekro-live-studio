import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn
from animations.blink_controller import BlinkController
from animations.body_swing_controller import BodySwingController
from animations.breathing_controller import BreathingController
from animations.mouth_expression_controller import MouthExpressionController
from clients.bilibili_live.bilibili_live import BilibiliLiveClient
from configs.config import config
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from services.animation_manager import animation_manager
from services.tweener import tweener
from services.vts_plugin import plugin
from services.websocket_manager import manager
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("应用启动中...")
    # 连接 VTS
    logger.info(f"正在连接到 VTube Studio, 地址: {config.PLUGIN.VTS_ENDPOINT} 请在VTube Studio中点击认证")
    if not await plugin.connect_and_authenticate():
        logger.error("连接 VTS 失败, 请检查 VTube Studio 是否已开启并加载API插件")
        sys.exit(1)

    # 启动 Tweener
    tweener.start(plugin)

    # 注册并启动空闲动画
    logger.info("正在注册动画控制器...")
    if config.BLINK.ENABLED:
        animation_manager.register_idle_controller(BlinkController())
    if config.BREATHING.ENABLED:
        animation_manager.register_idle_controller(BreathingController())
    if config.BODY_SWING.ENABLED:
        animation_manager.register_idle_controller(BodySwingController())
    if config.MOUTH_EXPRESSION.ENABLED:
        animation_manager.register_idle_controller(MouthExpressionController())

    asyncio.create_task(animation_manager.start_all())

    # 启动B站直播监听
    if config.BILIBILI_CONFIGS.LIVE_ROOM_ID and config.BILIBILI_CONFIGS.LIVE_ROOM_ID != "0":
        bili_client = BilibiliLiveClient()
        app.state.bilibili_client = bili_client
        asyncio.create_task(bili_client.start())
    else:
        app.state.bilibili_client = None
        logger.info("未配置B站直播间ID, 跳过B站直播监听")

    yield

    # Shutdown
    logger.info("应用关闭中...")
    await animation_manager.stop_all()
    tweener.release_all()
    await tweener.stop()
    if hasattr(app.state, "bilibili_client") and app.state.bilibili_client:
        await app.state.bilibili_client.stop()
    await plugin.disconnect()
    logger.info("应用已关闭")


app = FastAPI(lifespan=lifespan)


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


if __name__ == "__main__":
    logger.info(f"API服务器将在 http://{config.API.HOST}:{config.API.PORT} 上启动")
    uvicorn.run(
        "main:app",
        host=config.API.HOST,
        port=config.API.PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=True,
    )
