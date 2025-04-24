from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from configs.config import config
from services.animation_manager import AnimationManager
from services.plugin import plugin
from .schemas import AnimationRequest
from contextlib import asynccontextmanager
import animations.blink_controller as blink_mod
import animations.breathing_controller as breath_mod
import animations.body_swing_controller as body_mod
import animations.mouth_expression_controller as mouth_mod
from utils.logger import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化日志
    setup_logging(config.plugin.debug_mode)
    # 启动时认证插件并启动 idle 动画
    await plugin.connect_and_authenticate()
    global animation_manager
    animation_manager = AnimationManager()
    # 注册 idle 动画
    if config.blink.enabled:
        animation_manager.register_idle_controller(blink_mod.BlinkController())
    if config.breathing.enabled:
        animation_manager.register_idle_controller(breath_mod.BreathingController())
    if config.body_swing.enabled:
        animation_manager.register_idle_controller(body_mod.BodySwingController())
    if config.mouth_expression.enabled:
        animation_manager.register_idle_controller(mouth_mod.MouthExpressionController())
    await animation_manager.start()
    try:
        yield
    finally:
        # 关闭时停止动画并断开插件
        await animation_manager.stop()
        await plugin.disconnect()

app = FastAPI(
    title=config.plugin.plugin_name,
    version="1.0.0",
    description="VTS 面部控制插件 API",
    lifespan=lifespan
)

# 跨域设置（如有需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# 全局动画管理器
animation_manager: AnimationManager

@app.post("/animation")
async def post_animation(req: AnimationRequest):
    # 转换请求为内部动画格式
    data = {"actions": [], "loop": req.loop}
    for action in req.actions:
        data["actions"].append({
            "parameter": action.parameter,
            "from": action.from_value,
            "to": action.to,
            "duration": action.duration,
            "delay": action.delay,
            "easing": action.easing,
        })
    success = await animation_manager.run_animation(data)
    if not success:
        raise HTTPException(status_code=500, detail="运行动画失败")
    return {"success": True} 