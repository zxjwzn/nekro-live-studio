import asyncio
import logging
import signal
import traceback
from typing import Dict, Any, Optional, List

# 假设 vts_client 包在当前目录下或 Python 路径中
from vts_client import VTSPlugin, VTSClient, VTSException, APIError, ResponseError, ConnectionError
# 导入所有需要的模型类 (虽然现在用 plugin 方法，保留可能有助于理解)
from vts_client.exceptions import AuthenticationError
# from vts_client.models import (
#     StatisticsRequest, VTSFolderInfoRequest, APIStateRequest,
#     AvailableLive2dParametersRequest, FaceFoundRequest
# )

# --- 配置 ---
PLUGIN_NAME = "全面测试插件"
PLUGIN_DEVELOPER = "测试运行器"
VTS_ENDPOINT = "ws://localhost:8001"

# --- 日志设置 ---
# 使用 DEBUG 级别可以看到更多 VTSClient 内部日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_all")

# --- 全局变量 ---
plugin = VTSPlugin(
    plugin_name=PLUGIN_NAME,
    plugin_developer=PLUGIN_DEVELOPER,
    endpoint=VTS_ENDPOINT
)
# client 变量不再需要用于发送请求
# client: VTSClient = plugin.client 
shutdown_event = asyncio.Event()
original_model_id: Optional[str] = None # 用于恢复模型

# --- 事件处理函数 ---
async def on_test_event(event_data: dict):
    logger.info(f"[事件] 收到 TestEvent: {event_data.get('data')}")

async def on_model_loaded(event_data: dict):
    logger.info(f"[事件] 收到 ModelLoadedEvent: {event_data.get('data')}")

async def on_tracking_change(event_data: dict):
    logger.info(f"[事件] 收到 TrackingStatusChangedEvent: {event_data.get('data')}")

async def on_hotkey_triggered(event_data: dict):
    logger.info(f"[事件] 收到 HotkeyTriggeredEvent: {event_data.get('data')}")

# --- 测试辅助函数 ---
async def run_test_step(step_name: str, coro):
    logger.info(f"--- 开始测试步骤: {step_name} ---")
    await asyncio.sleep(1) # 每个小步骤前也稍作等待
    try:
        result = await coro
        logger.info(f"--- 完成测试步骤: {step_name} - 成功 (类型: {type(result)}) ---")
        # 对于返回字典或列表的，打印部分内容
        if isinstance(result, dict):
            # 避免打印过大的字典
            keys_to_show = list(result.keys())[:5] 
            preview = {k: result[k] for k in keys_to_show}
            logger.info(f"    结果预览 (前 {len(preview)} 键): {preview}")
        elif isinstance(result, list) and result:
            logger.info(f"    结果预览 (前 {min(len(result), 3)} 项): {result[:3]}")
        elif isinstance(result, bool):
             logger.info(f"    结果: {result}")
        # 其他类型不打印预览
        await asyncio.sleep(1) # 每个小步骤后也稍作等待
        return result
    except APIError as e:
        logger.error(f"--- 完成测试步骤: {step_name} - API 错误 ({e.error_id}): {e.error_message} ---")
    except (ResponseError, ConnectionError, AuthenticationError) as e:
         logger.error(f"--- 完成测试步骤: {step_name} - 客户端错误: {e} ---")
    except Exception as e:
        logger.error(f"--- 完成测试步骤: {step_name} - 未预料的错误: {e} ---")
        logger.error(traceback.format_exc())
    await asyncio.sleep(1) # 错误后也等待一下
    return None

# --- 主测试流程 ---
async def run_tests():
    global original_model_id

    # 注册所有测试事件的回调
    plugin.register_event_handler("TestEvent", on_test_event)
    plugin.register_event_handler("ModelLoadedEvent", on_model_loaded)
    plugin.register_event_handler("TrackingStatusChangedEvent", on_tracking_change)
    plugin.register_event_handler("HotkeyTriggeredEvent", on_hotkey_triggered)
    logger.info("已注册事件处理器")

    # 1. 连接与认证
    logger.info(">>> 阶段 1: 连接与认证 <<<")
    authenticated = await run_test_step("连接并认证", plugin.connect_and_authenticate())
    if not isinstance(authenticated, bool) or not authenticated:
        logger.critical("认证失败或返回类型错误，无法继续测试。")
        return
    logger.info(">>> 阶段 1 完成，等待 3 秒... <<<")
    await asyncio.sleep(3)

    # 2. 基本信息获取 (使用 plugin 方法)
    logger.info(">>> 阶段 2: 获取基本信息 <<<")
    await run_test_step("获取 API 状态", plugin.get_api_state())
    await run_test_step("获取统计信息", plugin.get_statistics())
    await run_test_step("获取 VTS 文件夹信息", plugin.get_folder_info())
    # is_face_found 直接返回 bool
    is_found = await run_test_step("检查是否检测到面部", plugin.is_face_found())
    # logger.info(f"面部检测结果: {is_found}") # run_test_step 会打印结果

    logger.info(">>> 阶段 2 完成，等待 3 秒... <<<")
    await asyncio.sleep(3)

    # 3. 模型操作
    logger.info(">>> 阶段 3: 模型操作 <<<")
    current_model_data = await run_test_step("获取当前模型", plugin.get_current_model())
    if isinstance(current_model_data, dict) and current_model_data.get("modelLoaded"):
        original_model_id = current_model_data.get("modelID")
        logger.info(f"初始加载的模型: ID={original_model_id}, 名称={current_model_data.get('modelName')}")
    else:
        logger.warning("初始没有加载模型或获取数据失败。")

    available_models = await run_test_step("获取可用模型列表", plugin.get_available_models())
    if isinstance(available_models, list) and available_models and len(available_models) > 1 and original_model_id:
        # 尝试加载一个不同的模型
        target_model = None
        for model in available_models:
            if isinstance(model, dict) and model.get("modelID") != original_model_id:
                target_model = model
                break
        if target_model:
            target_id = target_model.get("modelID")
            target_name = target_model.get('modelName')
            # 确保 target_id 是字符串
            if isinstance(target_id, str):
                logger.info(f"尝试加载不同模型: ID={target_id}, 名称={target_name}")
                await run_test_step(f"加载模型 {target_id}", plugin.load_model(target_id))
            else:
                logger.error(f"目标模型 {target_name} 的 ID 无效 (非字符串): {target_id}")
            logger.info("等待模型加载...")
            await asyncio.sleep(5) # 等待模型加载完成时间加长
        else:
            logger.warning("只有一个可用模型或者找不到不同的模型。")
    elif isinstance(available_models, list) and available_models and original_model_id is None:
        # 如果开始时没有模型，尝试加载第一个可用模型
        target_model = available_models[0]
        if isinstance(target_model, dict):
            target_id = target_model.get("modelID")
            target_name = target_model.get('modelName')
            # 确保 target_id 是字符串
            if isinstance(target_id, str):
                logger.info(f"尝试加载第一个可用模型: ID={target_id}, 名称={target_name}")
                await run_test_step(f"加载模型 {target_id}", plugin.load_model(target_id))
            else:
                logger.error(f"第一个可用模型 {target_name} 的 ID 无效 (非字符串): {target_id}")
            logger.info("等待模型加载...")
            await asyncio.sleep(5) # 等待模型加载完成时间加长
        else:
            logger.warning("第一个可用模型数据格式错误。")
    else:
        logger.warning("未找到可用模型、获取列表失败或无法执行模型加载测试。")
    logger.info(">>> 阶段 3 完成，等待 3 秒... <<<")
    await asyncio.sleep(3)


    # 4. 参数操作
    logger.info(">>> 阶段 4: 参数操作 <<<")
    input_params = await run_test_step("获取可用输入参数", plugin.get_available_parameters())
    # get_live2d_parameters 直接返回列表
    live2d_params = await run_test_step("获取可用 Live2D 参数", plugin.get_live2d_parameters())

    if isinstance(live2d_params, list) and live2d_params:
        logger.info(f"找到 {len(live2d_params)} 个 Live2D 参数。")
    else:
        logger.warning("未能获取或解析 Live2D 参数列表。")

    test_param_name = "FaceAngleX" # 一个通常存在的输入参数
    if isinstance(input_params, list) and any(isinstance(p, dict) and p.get("name") == test_param_name for p in input_params):
        param_details = await run_test_step(f"获取参数值 ({test_param_name})", plugin.get_parameter_value(test_param_name))
        if isinstance(param_details, dict):
            await run_test_step(f"设置参数值 ({test_param_name}, 模式=add, +5.0)", plugin.set_parameter_value(test_param_name, 5.0, mode="add"))
            await asyncio.sleep(1) # 等待参数变化生效
            await run_test_step(f"设置参数值 ({test_param_name}, 模式=add, -5.0, 恢复)", plugin.set_parameter_value(test_param_name, -5.0, mode="add"))
            await asyncio.sleep(1) # 等待参数变化生效
        else:
            logger.warning(f"获取参数 {test_param_name} 详情失败。")
    else:
        logger.warning(f"输入参数 '{test_param_name}' 未找到或列表格式错误，跳过参数设置/获取测试。")
    logger.info(">>> 阶段 4 完成，等待 3 秒... <<<")
    await asyncio.sleep(3)

    # 5. 表情操作
    logger.info(">>> 阶段 5: 表情操作 <<<")
    expressions = await run_test_step("获取表情列表", plugin.get_expressions())
    if isinstance(expressions, list) and expressions:
        first_expr = expressions[0]
        if isinstance(first_expr, dict):
            first_expr_file = first_expr.get("file")
            if first_expr_file:
                logger.info(f"第一个表情文件: {first_expr_file}")
                await run_test_step(f"获取单个表情状态 ({first_expr_file})", plugin.get_expressions(first_expr_file))
                await run_test_step(f"激活表情 ({first_expr_file})", plugin.activate_expression(first_expr_file, active=True))
                await asyncio.sleep(2) # 等待表情激活
                await run_test_step(f"停用表情 ({first_expr_file})", plugin.activate_expression(first_expr_file, active=False))
                await asyncio.sleep(2) # 等待表情停用
            else:
                logger.warning("第一个表情没有文件名。")
        else:
            logger.warning("第一个表情数据格式错误。")
    else:
        logger.warning("当前模型未找到表情或获取列表失败。")
    logger.info(">>> 阶段 5 完成，等待 3 秒... <<<")
    await asyncio.sleep(3)

    # 6. 热键操作
    logger.info(">>> 阶段 6: 热键操作 <<<")
    hotkeys = await run_test_step("获取热键列表", plugin.get_hotkeys())
    if isinstance(hotkeys, list) and hotkeys:
        first_hotkey = hotkeys[0]
        if isinstance(first_hotkey, dict):
            hotkey_id = first_hotkey.get("hotkeyID")
            hotkey_name = first_hotkey.get("name")
            if hotkey_id:
                logger.info(f"尝试触发第一个热键: ID={hotkey_id}, 名称={hotkey_name}")
                await run_test_step(f"触发热键 ({hotkey_id})", plugin.trigger_hotkey(hotkey_id))
                await asyncio.sleep(2) # 等待热键执行
            else:
                logger.warning("第一个热键没有 ID。")
        else:
            logger.warning("第一个热键数据格式错误。")
    else:
        logger.warning("当前模型未找到热键或获取列表失败。")
    logger.info(">>> 阶段 6 完成，等待 3 秒... <<<")
    await asyncio.sleep(3)

    # 7. 事件订阅测试
    logger.info(">>> 阶段 7: 事件订阅测试 <<<")
    logger.info("订阅 TestEvent, ModelLoadedEvent, TrackingStatusChangedEvent, HotkeyTriggeredEvent")
    try:
        # 分开订阅以便观察哪个失败 (使用 plugin 方法)
        await run_test_step("订阅 TestEvent", plugin.subscribe_event("TestEvent"))
        await run_test_step("订阅 ModelLoadedEvent", plugin.subscribe_event("ModelLoadedEvent"))
        await run_test_step("订阅 TrackingStatusChangedEvent", plugin.subscribe_event("TrackingStatusChangedEvent"))
        await run_test_step("订阅 HotkeyTriggeredEvent", plugin.subscribe_event("HotkeyTriggeredEvent"))

        logger.info("订阅请求已发送。等待事件...")
        logger.info(">>> 请现在在 VTube Studio 中执行操作 <<<")
        logger.info(">>> (例如：加载/卸载模型, 触发热键, 遮挡/移开面部) <<<")
        logger.info(">>> 等待 15 秒接收事件... <<<")
        await asyncio.sleep(15) # 等待 15 秒接收事件

        logger.info("取消订阅 TestEvent...")
        await run_test_step("取消订阅 TestEvent", plugin.unsubscribe_event("TestEvent"))
        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"事件订阅/等待期间出错: {e}")
    logger.info("--- 事件订阅测试完成 ---")
    logger.info(">>> 阶段 7 完成，等待 3 秒... <<<")
    await asyncio.sleep(3)


    # --- 测试结束，恢复模型 ---
    logger.info(">>> 阶段 8: 清理 <<<")
    if original_model_id:
        logger.info(f"尝试恢复初始模型: ID={original_model_id}")
        await run_test_step(f"加载原始模型 {original_model_id}", plugin.load_model(original_model_id))
        await asyncio.sleep(5)
    else:
        # 如果开始时没有模型，尝试卸载当前模型
        current_model_data = await plugin.get_current_model()
        if isinstance(current_model_data, dict) and current_model_data.get("modelLoaded"):
            logger.info("尝试卸载当前加载的模型...")
            await run_test_step("卸载模型", plugin.load_model(""))
            await asyncio.sleep(3)

    logger.info("所有计划的测试步骤已完成。")
    shutdown_event.set()


# --- 主程序 ---
async def main():
    """主程序入口"""
    logger.info("启动全面测试套件...")
    try:
        await run_tests()
    except Exception as e:
        logger.critical(f"测试套件因未处理的异常而失败: {e}", exc_info=True)
    finally:
        logger.info("开始清理...")
        try:
            # 尝试取消订阅所有事件
            if plugin.client.is_authenticated:
                logger.info("正在取消订阅所有事件...")
                await plugin.unsubscribe_event() # 使用 plugin 方法
        except Exception as e:
            logger.warning(f"取消订阅事件时出错: {e}")
        
        # 断开连接
        await plugin.disconnect()
        logger.info("测试客户端已关闭。")

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
