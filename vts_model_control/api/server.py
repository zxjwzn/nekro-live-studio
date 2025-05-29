from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from typing import List, Optional, Dict, Any
import json
from configs.config import config
from services.animation_manager import AnimationManager
from services.plugin import plugin
from .ws_schemas import (
    SayAction,
    AnimationAction,
    EmotionAction,
    ExecuteAction,
    ClearAction,
)
from services.audio_player import AudioManager
from services.websocket_manager import manager as websocket_manager
from contextlib import asynccontextmanager
import asyncio
import animations.blink_controller as blink_mod
import animations.breathing_controller as breath_mod
import animations.body_swing_controller as body_mod
import animations.mouth_expression_controller as mouth_mod
from utils.logger import setup_logging, logger

# 导入B站直播弹幕监听模块
from client.bilibili_live import start_bilibili_live, stop_bilibili_live


@asynccontextmanager
async def lifespan(app: FastAPI):
    global animation_manager, audio_player
    # 阶段1：初始化日志和认证插件
    setup_logging(config.plugin.debug_mode)
    logger.info(f"启动插件: {config.plugin.plugin_name}")

    # 启动时认证插件并启动 idle 动画
    await plugin.connect_and_authenticate()

    # 阶段2：初始化动画管理器和idle动画
    animation_manager = AnimationManager()
    # 注册 idle 动画
    if config.blink.enabled:
        animation_manager.register_idle_controller(blink_mod.BlinkController(), False)
    if config.breathing.enabled:
        animation_manager.register_idle_controller(
            breath_mod.BreathingController(), True
        )
    if config.body_swing.enabled:
        animation_manager.register_idle_controller(body_mod.BodySwingController(), True)
    if config.mouth_expression.enabled:
        animation_manager.register_idle_controller(
            mouth_mod.MouthExpressionController(), False
        )
    await animation_manager.start()
    logger.info("AnimationManager 已启动并注册idle动画。")

    # 阶段3：初始化音频播放器
    if config.speech_synthesis.enabled:
        logger.info("语音合成功能已启用。正在初始化AudioManager...")
        try:
            audio_player = AudioManager(
                rpg_sound_file_path=config.speech_synthesis.audio_file_path,
                default_text_rate=config.speech_synthesis.text_per_second_rate,
                default_volume=config.speech_synthesis.volume,
            )
            logger.info("AudioManager 初始化成功。")
        except Exception as e:
            logger.error(f"AudioManager 初始化失败: {e}")
            audio_player = None
    else:
        logger.info("语音合成功能未启用。")

    # 阶段4：启动B站直播弹幕监听
    if config.bilibili_configs.live_room_id != 0:
        logger.info(
            f"正在启动B站直播弹幕监听，房间ID: {config.bilibili_configs.live_room_id}"
        )
        try:
            await start_bilibili_live()
        except Exception as e:
            logger.error(f"启动B站直播弹幕监听失败: {e}")

    try:
        yield
    finally:
        # 阶段4：关闭插件
        logger.info("开始关闭插件...")

        # 停止B站直播弹幕监听
        try:
            await stop_bilibili_live()
            logger.info("已停止B站直播弹幕监听。")
        except Exception as e:
            logger.error(f"停止B站直播弹幕监听出错: {e}")

        if audio_player:
            audio_player.stop_all_sounds()
            logger.info("AudioManager 已停止所有声音。")
        await animation_manager.stop()
        logger.info("AnimationManager 已停止。")
        await plugin.disconnect()
        logger.info("插件已断开连接。插件关闭完成。")


app = FastAPI(
    title=config.plugin.plugin_name,
    version="1.0.0",
    description="VTS 面部控制插件 API",
    lifespan=lifespan,
)

# 跨域设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# 全局动画管理器和音频播放器实例
animation_manager: AnimationManager
audio_player: Optional[AudioManager] = None

# 存储每个WebSocket连接的动作队列
ws_action_queues: Dict[WebSocket, List[Dict[str, Any]]] = {}


# 字幕WebSocket接口
@app.websocket("/ws/subtitles")
async def websocket_subtitle_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket, "subtitles")
    logger.info("新的WebSocket客户端连接到 /ws/subtitles")
    try:
        while True:
            await asyncio.sleep(0.1)  # Keep connection alive
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket客户端断开连接 /ws/subtitles")
    except Exception as e:
        logger.error(f"WebSocket错误 /ws/subtitles: {e}")
        websocket_manager.disconnect(websocket)


# 新增：弹幕WebSocket接口
@app.websocket("/ws/danmaku")
async def websocket_danmaku_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket, "danmaku")  # 指定为danmaku路径分组
    logger.info("新的WebSocket客户端连接到 /ws/danmaku")
    try:
        while True:
            # 这个端点主要用于接收广播，所以大部分时间是等待
            # 如果需要此端点也接收来自客户端的消息，可以在这里添加 await websocket.receive_text()等逻辑
            await asyncio.sleep(0.1)  # Keep connection alive, server pushes data
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket客户端断开连接 /ws/danmaku")
    except Exception as e:
        logger.error(f"WebSocket错误 /ws/danmaku: {e}")
        websocket_manager.disconnect(websocket)


# 动画控制WebSocket接口
@app.websocket("/ws/animate_control")
async def websocket_animate_control(websocket: WebSocket):
    await websocket.accept()
    ws_action_queues[websocket] = []
    logger.info("新的WebSocket客户端连接到 /ws/animate_control")

    try:
        while True:
            # 阶段1：接收并解析消息
            data = await websocket.receive_text()
            try:
                # 首先解析JSON，然后尝试验证为一个WSMessage类型
                message_json = json.loads(data)
                message_type = message_json.get("type", "")

                # 阶段2：根据消息类型处理不同的动作
                if message_type == "say":
                    message = SayAction.model_validate(message_json)
                    await handle_say_message(websocket, message)

                elif message_type == "animation":
                    message = AnimationAction.model_validate(message_json)
                    await handle_animation_message(websocket, message)

                elif message_type == "emotion":
                    message = EmotionAction.model_validate(message_json)
                    await handle_emotion_message(websocket, message)

                elif message_type == "execute":
                    message = ExecuteAction.model_validate(message_json)
                    success = await execute_actions(websocket, message)
                    if success:
                        await websocket.send_json(
                            {"status": "success", "message": "Actions executed"}
                        )
                    else:
                        await websocket.send_json(
                            {"status": "error", "message": "Failed to execute actions"}
                        )

                elif message_type == "clear":
                    message = ClearAction.model_validate(message_json)
                    ws_action_queues[websocket] = []
                    await websocket.send_json(
                        {"status": "success", "message": "Action queue cleared"}
                    )

                else:
                    await websocket.send_json(
                        {"status": "error", "message": f"未知消息类型: {message_type}"}
                    )

            except json.JSONDecodeError:
                await websocket.send_json(
                    {"status": "error", "message": "无效的JSON格式"}
                )
            except Exception as e:
                logger.error(f"处理WebSocket消息时发生错误: {e}")
                await websocket.send_json(
                    {"status": "error", "message": f"处理消息时出错: {str(e)}"}
                )

    except WebSocketDisconnect:
        logger.info("WebSocket客户端断开连接 /ws/animate_control")
    except Exception as e:
        logger.error(f"WebSocket错误 /ws/animate_control: {e}")
    finally:
        if websocket in ws_action_queues:
            del ws_action_queues[websocket]


async def handle_say_message(websocket: WebSocket, message: SayAction):
    """处理说话类型的消息"""
    action = {
        "type": "say",
        "text": message.data.text,
        "speeds": message.data.speed,  # 转换为AnimationManager期望的格式
        "startTime": message.data.delay,
    }

    ws_action_queues[websocket].append(action)
    logger.debug(f"添加Say动作: {message.data.text[:1]} at {message.data.delay}s")
    await websocket.send_json({"status": "success", "message": "Say action added"})


async def handle_animation_message(websocket: WebSocket, message: AnimationAction):
    """处理动画类型的消息"""
    animation_data_list = message.data
    if not isinstance(animation_data_list, list):
        animation_data_list = [animation_data_list]

    for anim_data in animation_data_list:
        action = {
            "type": "animation",
            "parameter": anim_data.parameter,
            "from": anim_data.from_value,
            "to": anim_data.to,
            "duration": anim_data.duration,
            "startTime": anim_data.delay,
            "easing": anim_data.easing,
        }

        ws_action_queues[websocket].append(action)
        logger.debug(f"添加Animation动作: {anim_data.parameter} at {anim_data.delay}s")

    await websocket.send_json({"status": "success", "message": "动画动作已添加"})


async def handle_emotion_message(websocket: WebSocket, message: EmotionAction):
    """处理表情类型的消息"""
    # 检查是否只有type，没有name参数（或name为None/空）
    if not message.data.name:
        try:
            # 返回所有表情列表
            expressions = await plugin.get_expressions()
            await websocket.send_json({
                "status": "success", 
                "message": "表情列表已获取",
                "data": {
                    "type": "emotion",
                    "expressions": expressions
                }
            })
            return
        except Exception as e:
            logger.error(f"获取表情列表时发生错误: {e}")
            await websocket.send_json({
                "status": "error", 
                "message": f"获取表情列表失败: {str(e)}"
            })
            return
    
    # 原有逻辑：添加表情动作到队列
    action = {
        "type": "emotion",
        "name": message.data.name,
        "duration": message.data.duration,
        "startTime": message.data.delay,
    }

    ws_action_queues[websocket].append(action)
    logger.debug(f"添加Emotion动作: {message.data.name} at {message.data.delay}s")
    await websocket.send_json({"status": "success", "message": "表情动作已添加"})


async def execute_actions(websocket: WebSocket, message: ExecuteAction) -> bool:
    """执行累积的动作"""
    if websocket not in ws_action_queues or not ws_action_queues[websocket]:
        return True  # 队列为空，认为执行成功

    # 获取loop参数
    loop = message.data.loop

    # 新增：确保眨眼控制器完成当前周期并回到睁眼状态
    for controller in animation_manager.idle_controllers:
        if not controller.skip_pause:  # 眨眼和嘴部表情控制器的skip_pause为False
            # 暂停控制器，但允许完成当前周期中的关键动作
            current_task = controller._task
            if current_task and not current_task.done():
                current_task.cancel()  # 触发CancelledError，控制器会处理完关键动作
                # 给予足够时间完成关键动作（眨眼完成到睁眼状态）
                if hasattr(controller, "cfg") and hasattr(
                    controller.cfg, "open_duration"
                ):
                    await asyncio.sleep(controller.cfg.open_duration + 0.1)
                else:
                    await asyncio.sleep(0.3)  # 默认等待时间

    # 阶段1：准备动作数据
    actions = ws_action_queues[websocket]
    animation_actions_for_manager = []
    audio_tasks = []

    for action in actions:
        action_type = action.get("type", "")

        if action_type == "animation":
            animation_actions_for_manager.append(
                {
                    "type": "animation",
                    "parameter": action.get("parameter"),
                    "from": action.get("from"),
                    "to": action.get("to"),
                    "duration": action.get("duration"),
                    "startTime": action.get("startTime"),
                    "easing": action.get("easing"),
                }
            )

        elif action_type == "emotion":
            animation_actions_for_manager.append(
                {
                    "type": "emotion",
                    "name": action.get("name"),
                    "duration": action.get("duration"),
                    "startTime": action.get("startTime"),
                }
            )

        elif action_type == "say":
            # 处理字幕广播
            subtitle_data = {
                "type": "subtitles",
                "payload": {
                    "texts": action.get("text", []),
                    "speeds": action.get("speeds", []),
                    "actionStartTime": action.get("startTime", 0.0),
                },
            }
            asyncio.create_task(websocket_manager.broadcast_json_to_path("subtitles", subtitle_data))

            # 处理语音合成
            if audio_player and config.speech_synthesis.enabled:
                current_audio_player = audio_player

                async def delayed_speech_task(current_action):
                    if not current_audio_player:
                        return
                    try:
                        if current_action.get("startTime", 0) > 0:
                            await asyncio.sleep(current_action.get("startTime", 0))
                        await current_audio_player.play_text_as_speech(
                            current_action.get("text", []),
                            current_action.get("speeds", []),
                        )
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"播放语音时发生错误: {e}")

                audio_tasks.append(asyncio.create_task(delayed_speech_task(action)))

    # 阶段2：执行动画
    animation_successful = True
    if animation_actions_for_manager:
        data_for_manager = {"actions": animation_actions_for_manager, "loop": loop}
        try:
            success = await animation_manager.run_animation(data_for_manager)
            if not success:
                animation_successful = False
        except Exception as e:
            animation_successful = False
            logger.error(f"调用AnimationManager时发生异常: {e}")

    # 阶段3：处理音频任务
    if audio_tasks:
        await asyncio.gather(*audio_tasks, return_exceptions=True)

    # 阶段4：清空队列
    ws_action_queues[websocket] = []

    return animation_successful


# 设置前端静态文件服务
current_script_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir_path = os.path.join(current_script_dir, "..", "frontend")

if os.path.exists(frontend_dir_path) and os.path.isdir(frontend_dir_path):
    app.mount(
        "/frontend", StaticFiles(directory=frontend_dir_path), name="frontend_static"
    )
    logger.info(f"前端静态文件已从以下路径挂载: {frontend_dir_path}, 可在/frontend访问")
else:
    logger.warning(f"前端目录{frontend_dir_path}未找到。静态文件将无法提供。")


# 字幕显示页面
@app.get("/subtitles-display", response_class=HTMLResponse)
async def get_subtitles_page():
    subtitle_html_path = os.path.join(frontend_dir_path, "subtitles.html")
    if os.path.exists(subtitle_html_path):
        with open(subtitle_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    logger.error(f"未在{subtitle_html_path}找到subtitles.html")
    raise HTTPException(status_code=404, detail="未找到字幕显示页面。")
