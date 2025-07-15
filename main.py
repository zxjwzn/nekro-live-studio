import asyncio
import os
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from nekro_live_studio.api.websockets import router as websockets_router
from nekro_live_studio.clients.live.bilibili.live import bilibili_live_client
from nekro_live_studio.clients.music.netease_cloud.music import (
    netease_cloud_music_client,
)
from nekro_live_studio.clients.vtube_studio.plugin import plugin
from nekro_live_studio.configs.config import config, save_config
from nekro_live_studio.controllers.config_manager import config_manager
from nekro_live_studio.services.controller_manager import controller_manager
from nekro_live_studio.services.tweener import tweener
from nekro_live_studio.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Startup
    logger.info("应用启动中...")

    await netease_cloud_music_client.start()
    await netease_cloud_music_client.download_song(2619664909, "where we began")
    await bilibili_live_client.start()

    # 连接 VTS
    logger.info(f"正在连接到 VTube Studio, 地址: {config.PLUGIN.VTS_ENDPOINT} 请在VTube Studio中点击认证")
    if not await plugin.connect_and_authenticate(config.PLUGIN.AUTHENTICATION_TOKEN):
        logger.warning("连接 VTS 失败, 请检查 VTube Studio 是否已开启并加载API插件 或 检查认证token是否正确")
        sys.exit(1)

    # 自动搜索和注册所有控制器
    controller_manager.auto_discover_and_register_controllers()

    await config_manager.load_config_for_current_model()

    if plugin.client.authentication_token:
        config.PLUGIN.AUTHENTICATION_TOKEN = plugin.client.authentication_token

    # 注册模型切换事件处理器
    logger.info("注册模型切换事件处理器...")
    plugin.register_event_handler("ModelLoadedEvent", config_manager.on_model_loaded_event)
    
    # 订阅模型切换事件
    try:
        await plugin.subscribe_event("ModelLoadedEvent")
        logger.info("已成功订阅模型切换事件，将自动加载对应模型的配置。")
    except Exception as e:
        logger.error(f"订阅模型切换事件失败: {e}", exc_info=True)
        logger.warning("模型切换时将不会自动加载配置，但程序会继续运行。")
    
    # 启动 Tweener
    tweener.start()
    await controller_manager.start_all_idle()

    logger.info("应用启动完成")
    logger.info(f"字幕页面位于 http://{config.API.HOST}:{config.API.PORT}/static/frontend/index.html 请在浏览器或是OBS中使用浏览器源打开")
    logger.info(f"控制端 WebSocket 地址为 ws://{config.API.HOST}:{config.API.PORT} 请在Nekro-Agent的webui界面填写")
    yield

    # Shutdown
    logger.info("应用关闭中...")

    # 清理临时文件
    logger.info("清理临时文件中...")
    temp_dir = Path("data/temp")
    if Path(temp_dir).exists():
        for file_path in Path(temp_dir).iterdir():
            try:
                if file_path.is_file() or file_path.is_symlink():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f"清理临时文件失败 {file_path}. 原因: {e}")

    save_config()
    await controller_manager.stop_all_idle()
    tweener.release_all()
    await tweener.stop()
    
    # 取消订阅事件
    try:
        await plugin.unsubscribe_event("ModelLoadedEvent")
        logger.info("已取消订阅模型切换事件。")
    except Exception as e:
        logger.error(f"取消订阅模型切换事件失败: {e}", exc_info=True)
    
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