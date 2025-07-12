import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from nekro_live_studio.api.websockets import router as websockets_router
from nekro_live_studio.clients.live.bilibili_live import bilibili_live_client
from nekro_live_studio.clients.vtube_studio.plugin import plugin
from nekro_live_studio.configs.config import config, save_config
from nekro_live_studio.controllers.config_manager import config_manager
from nekro_live_studio.controllers.controllers.blink_controller import BlinkController
from nekro_live_studio.controllers.controllers.body_swing_controller import (
    BodySwingController,
)
from nekro_live_studio.controllers.controllers.breathing_controller import (
    BreathingController,
)
from nekro_live_studio.controllers.controllers.mouth_expression_controller import (
    MouthExpressionController,
)
from nekro_live_studio.controllers.controllers.mouth_sync import MouthSyncController
from nekro_live_studio.services.controller_manager import controller_manager
from nekro_live_studio.services.tweener import tweener
from nekro_live_studio.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("应用启动中...")
    # 连接 VTS
    logger.info(f"正在连接到 VTube Studio, 地址: {config.PLUGIN.VTS_ENDPOINT} 请在VTube Studio中点击认证")
    if not await plugin.connect_and_authenticate(config.PLUGIN.AUTHENTICATION_TOKEN):
        logger.warning("连接 VTS 失败, 请检查 VTube Studio 是否已开启并加载API插件 或 检查认证token是否正确")
        sys.exit(1)

    await config_manager.load_config_for_current_model()

    if plugin.client.authentication_token:
        config.PLUGIN.AUTHENTICATION_TOKEN = plugin.client.authentication_token
        save_config()
    # 启动 Tweener
    tweener.start()

    controller_manager.register_controller(BlinkController())
    controller_manager.register_controller(BodySwingController())
    controller_manager.register_controller(BreathingController())
    controller_manager.register_controller(MouthExpressionController())
    controller_manager.register_controller(MouthSyncController())

    asyncio.create_task(controller_manager.start_all_idle())
    asyncio.create_task(bilibili_live_client.start())
    logger.info("应用启动完成")
    logger.info(f"字幕页面位于 http://{config.API.HOST}:{config.API.PORT}/static/frontend/index.html 请在浏览器或是OBS中使用浏览器源打开")
    logger.info(f"控制端 WebSocket 地址为 ws://{config.API.HOST}:{config.API.PORT} 请在Nekro-Agent的webui界面填写")
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

# 包含 WebSocket 路由
app.include_router(websockets_router)


if __name__ == "__main__":
    logger.info(f"API服务器将在 http://{config.API.HOST}:{config.API.PORT} 上启动")
    uvicorn.run(
        app,
        host=config.API.HOST,
        port=config.API.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )