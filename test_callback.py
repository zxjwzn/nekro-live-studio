import asyncio
import logging
import signal

# 假设你的 vts_client 包在当前目录下或 Python 路径中
from vts_client import VTSPlugin, AuthenticationError, ConnectionError, APIError, ResponseError

# --- 配置 ---
PLUGIN_NAME = "MyEventExamplePlugin"
PLUGIN_DEVELOPER = "YourName"
VTS_ENDPOINT = "ws://localhost:8001"
EVENT_TO_SUBSCRIBE = "ModelLoadedEvent"

# --- 日志设置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("event_example")

# --- 全局变量 ---
plugin = VTSPlugin(
    plugin_name=PLUGIN_NAME,
    plugin_developer=PLUGIN_DEVELOPER,
    endpoint=VTS_ENDPOINT
)
shutdown_event = asyncio.Event() # 用于优雅关闭

# --- 事件处理函数 ---
async def on_model_loaded(event_data: dict) -> None:
    """
    处理 ModelLoadedEvent 的回调函数
    """
    try:
        data = event_data.get("data", {})
        model_loaded = data.get("modelLoaded", False)
        model_name = data.get("modelName", "N/A")
        model_id = data.get("modelID", "N/A")
        
        if model_loaded:
            logger.info(f"事件: 模型已加载 - 名称: {model_name}, ID: {model_id}")
        else:
            logger.info(f"事件: 模型已卸载 - 名称: {model_name}, ID: {model_id}")
            
    except Exception as e:
        logger.error(f"处理 {EVENT_TO_SUBSCRIBE} 时出错: {e}", exc_info=True)

# --- 主程序 ---
async def main():
    """主程序，连接、认证、订阅事件并保持运行"""
    logger.info("启动插件...")

    # 注册事件处理函数 (在连接前注册)
    plugin.register_event_handler(EVENT_TO_SUBSCRIBE, on_model_loaded)
    logger.info(f"已注册 {EVENT_TO_SUBSCRIBE} 的处理函数")

    try:
        # 1. 连接并认证
        logger.info("正在连接并认证...")
        authenticated = await plugin.connect_and_authenticate()
        
        if not authenticated:
            logger.error("认证失败，请检查 VTube Studio 是否允许插件连接以及 Token 是否正确。")
            return # 认证失败，退出

        logger.info("认证成功！")

        # 2. 订阅事件
        logger.info(f"正在订阅事件: {EVENT_TO_SUBSCRIBE}...")
        try:
            subscribe_response = await plugin.client.subscribe_to_event(EVENT_TO_SUBSCRIBE)
            logger.info(f"事件订阅成功。当前订阅的事件: {subscribe_response.subscribed_events}")
        except APIError as e:
            logger.error(f"订阅事件 {EVENT_TO_SUBSCRIBE} 失败 (API错误): {e}")
            # 可以选择在这里退出或继续运行但不接收该事件
        except (ResponseError, ConnectionError) as e:
            logger.error(f"订阅事件 {EVENT_TO_SUBSCRIBE} 失败 (连接/响应错误): {e}")
            # 连接或响应错误，可能需要退出
            return
        except Exception as e:
            logger.error(f"订阅事件 {EVENT_TO_SUBSCRIBE} 时发生未知错误: {e}", exc_info=True)
            # 未知错误，可能需要退出
            return

        # 3. 保持运行直到收到关闭信号
        logger.info("插件正在运行，等待事件... 按 Ctrl+C 关闭。")
        await shutdown_event.wait() # 等待关闭事件被设置

    except AuthenticationError as e:
        logger.error(f"认证过程中出错: {e}")
    except ConnectionError as e:
        logger.error(f"连接错误: {e}")
    except Exception as e:
        logger.error(f"插件运行时发生未预料的错误: {e}", exc_info=True)
    finally:
        logger.info("正在关闭插件...")
        try:
            # 尝试取消订阅所有事件（可选）
            if plugin.client.is_authenticated:
                logger.info("正在取消订阅所有事件...")
                await plugin.client.unsubscribe_from_event()
        except Exception as e:
            logger.warning(f"取消订阅事件时出错: {e}")
        
        # 断开连接
        await plugin.disconnect()
        logger.info("插件已关闭。")

# --- 信号处理 ---
def handle_signal(sig, frame):
    """处理 SIGINT (Ctrl+C) 和 SIGTERM"""
    logger.info(f"收到信号 {sig}, 准备关闭...")
    # 不要在这里直接调用 await，设置事件让主循环处理关闭
    shutdown_event.set()

# --- 入口点 ---
if __name__ == "__main__":
    # 设置信号处理
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # 运行主异步函数
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 冗余处理，以防信号处理未完全捕获
        logger.info("通过 KeyboardInterrupt 关闭")
