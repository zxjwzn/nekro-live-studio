#待重构
import asyncio
import logging
import signal
import random
import math
import traceback
from typing import Optional

# 假设 vts_client 包在当前目录下或 Python 路径中
from vts_client import VTSPlugin, VTSException, APIError, ResponseError, ConnectionError, AuthenticationError
from easing import ease_out_sine, ease_in_sine, ease_in_out_sine, ease_in_out_quad, ease_in_out_cubic, ease_in_out_elastic, ease_in_out_back, ease_in_out_bounce

# --- 配置 ---
PLUGIN_NAME = "自动眨眼、呼吸与身体摇摆插件"
PLUGIN_DEVELOPER = "迁移自BlinkingClient"
DEFAULT_VTS_ENDPOINT = "ws://localhost:8002"

# --- 眨眼配置 ---
BLINK_ENABLED = True  # 是否启用眨眼效果
MIN_INTERVAL = 2.0  # 两次眨眼之间的最小间隔时间（秒）
MAX_INTERVAL = 4.0  # 两次眨眼之间的最大间隔时间（秒）
CLOSE_DURATION = 0.15  # 闭眼动画持续时间（秒）
OPEN_DURATION = 0.3  # 睁眼动画持续时间（秒）
CLOSED_HOLD = 0.05  # 眼睛闭合状态的保持时间（秒）
DEBUG_MODE = False  # 是否启用调试模式

# --- 呼吸配置 ---
BREATHING_ENABLED = True  # 是否启用呼吸效果
BREATHING_MIN_VALUE = -3.0  # 呼吸参数最小值（呼气）
BREATHING_MAX_VALUE = 3.0  # 呼吸参数最大值（吸气）
BREATHING_INHALE_DURATION = 2.0  # 吸气持续时间（秒）
BREATHING_EXHALE_DURATION = 2.5  # 呼气持续时间（秒）
BREATHING_PARAMETER = "FaceAngleY"  # 呼吸控制的参数名

# --- 身体摇摆配置 ---
BODY_SWING_ENABLED = True  # 是否启用身体摇摆效果
BODY_SWING_X_MIN = -10.0  # 身体左右摇摆最小位置（左侧）
BODY_SWING_X_MAX = 15.0  # 身体左右摇摆最大位置（右侧）
BODY_SWING_Z_MIN = -10.0  # 上肢旋转最小位置（下方）
BODY_SWING_Z_MAX = 15.0  # 上肢旋转最大位置（上方）
BODY_SWING_MIN_DURATION = 2.0  # 摇摆最短持续时间（秒）
BODY_SWING_MAX_DURATION = 8.0  # 摇摆最长持续时间（秒）
BODY_SWING_X_PARAMETER = "FaceAngleX"  # 身体左右摇摆控制的参数名
BODY_SWING_Z_PARAMETER = "FaceAngleZ"  # 上肢旋转控制的参数名

# --- 眼睛跟随摇摆配置 ---
EYE_FOLLOW_ENABLED = True  # 是否启用眼睛跟随身体摇摆
EYE_X_MIN_RANGE = -1.0  # 眼睛左右移动最小值（左侧）
EYE_X_MAX_RANGE = 1.0  # 眼睛左右移动最大值（右侧）
EYE_Y_MIN_RANGE = -1.0  # 眼睛上下移动最小值（下方）
EYE_Y_MAX_RANGE = 1.0  # 眼睛上下移动最大值（上方）
EYE_LEFT_X_PARAMETER = "EyeLeftX"  # 左眼水平移动参数
EYE_RIGHT_X_PARAMETER = "EyeRightX"  # 右眼水平移动参数
EYE_LEFT_Y_PARAMETER = "EyeLeftY"  # 左眼垂直移动参数
EYE_RIGHT_Y_PARAMETER = "EyeRightY"  # 右眼垂直移动参数

# --- 嘴部表情配置 ---
MOUTH_EXPRESSION_ENABLED = True  # 是否启用嘴部表情变化
MOUTH_SMILE_MIN = 0.1  # 嘴角微笑最小值（不高兴）
MOUTH_SMILE_MAX = 0.7  # 嘴角微笑最大值（高兴）
MOUTH_OPEN_MIN = 0.1  # 嘴巴开合最小值（闭合）
MOUTH_OPEN_MAX = 0.7  # 嘴巴开合最大值（张开，可调小避免过度张嘴）
MOUTH_CHANGE_MIN_DURATION = 2.0  # 表情变化最短持续时间（秒）
MOUTH_CHANGE_MAX_DURATION = 7.0  # 表情变化最长持续时间（秒）
MOUTH_SMILE_PARAMETER = "MouthSmile"  # 嘴角微笑控制的参数名
MOUTH_OPEN_PARAMETER = "MouthOpen"    # 嘴巴开合控制的参数名

# --- 日志设置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlinkingPlugin")
if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    logging.getLogger("vts_client").setLevel(logging.DEBUG)

# --- 全局变量 ---
plugin: Optional[VTSPlugin] = None
shutdown_event = asyncio.Event()
blink_active = False
breathing_active = False
body_swing_active = False
mouth_expression_active = False
# 当前身体摇摆位置
current_x_position = 0.0
current_z_position = 0.0
# 当前眼睛位置
current_eye_x_position = 0.0
current_eye_y_position = 0.0
# 当前嘴部表情
current_mouth_smile = 0.0
current_mouth_open = 0.0
start_parameters = []
# --- 核心眨眼逻辑 ---
async def blink_cycle(plugin: VTSPlugin, close_duration: float = 0.08, open_duration: float = 0.08, closed_hold: float = 0.05):
    """执行一次带有缓动效果的完整眨眼周期 (异步)，结束后保持睁眼"""

    logger.info("开始眨眼周期")

    # --- 眨眼动画 ---
    try:
        # 1. 闭眼 (使用 ease_out_sine 从 1.0 过渡到 0.0)
        logger.info("开始闭眼 (缓动 1.0 -> 0.0)")
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + close_duration
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / close_duration)
            value = 1.0 * (1.0 - ease_in_sine(progress)) # 值从 1.0 降到 0.0

            # 使用 plugin.set_parameter_value 设置参数
            try:
                await plugin.set_parameter_value("EyeOpenLeft", value, mode="set")
                await plugin.set_parameter_value("EyeOpenRight", value, mode="set")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置闭眼参数时出错: {e}")
                return # 出错则中断本次眨眼
                
            # 计算需要等待的时间，保证动画平滑但不超过总时长
            next_step_time = min(current_time + 0.016, end_time)  # 约60fps，最多等待16ms
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # 确保完全闭合
        try:
            await plugin.set_parameter_value("EyeOpenLeft", 0.0)
            await plugin.set_parameter_value("EyeOpenRight", 0.0)
        except (APIError, ResponseError, ConnectionError) as e:
            logger.error(f"设置完全闭眼参数时出错: {e}")
            # 即使这里出错，也继续尝试睁眼

        # 2. 保持闭眼
        logger.info("保持闭眼")
        await asyncio.sleep(closed_hold)

        # 3. 睁眼 (使用 ease_in_sine 从 0.0 过渡到 1.0)
        logger.info("开始睁眼 (缓动 0.0 -> 1.0)")
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + open_duration
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / open_duration)
            value = 1.0 * ease_in_sine(progress) # 值从 0.0 升到 1.0

            try:
                await plugin.set_parameter_value("EyeOpenLeft", value, mode="set")
                await plugin.set_parameter_value("EyeOpenRight", value, mode="set")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置睁眼参数时出错: {e}")
                return # 出错则中断本次眨眼
                
            # 计算需要等待的时间，保证动画平滑但不超过总时长
            next_step_time = min(current_time + 0.016, end_time)  # 约60fps，最多等待16ms
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # --- 动画结束，确保眼睛是睁开状态 (1.0) ---
        logger.info("眨眼动画完成，确保眼睛保持睁开")
        try:
            await plugin.set_parameter_value("EyeOpenLeft", 1.0)
            await plugin.set_parameter_value("EyeOpenRight", 1.0)
            logger.info("眼睛状态已最终设置为睁开")
        except (APIError, ResponseError, ConnectionError) as e:
            logger.error(f"设置最终睁眼状态时出错: {e}")

    except Exception as e:
        logger.error(f"执行眨眼周期时发生意外错误: {e}")
        logger.error(traceback.format_exc())

# --- 呼吸效果逻辑 ---
async def breathing_cycle(plugin: VTSPlugin):
    """执行一次完整的呼吸周期（吸气-呼气）"""
    logger.info("开始呼吸周期")
    
    try:
        # 1. 吸气阶段（从BREATHING_MIN_VALUE增加到BREATHING_MAX_VALUE）
        logger.info(f"开始吸气 ({BREATHING_MIN_VALUE} -> {BREATHING_MAX_VALUE})")
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + BREATHING_INHALE_DURATION
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / BREATHING_INHALE_DURATION)
            
            # 使用ease_in_sine计算当前值
            delta = (BREATHING_MAX_VALUE - BREATHING_MIN_VALUE) * ease_in_out_sine(progress)
            value = BREATHING_MIN_VALUE + delta
            
            # 使用add模式设置参数，不影响其他动作
            try:
                await plugin.set_parameter_value(BREATHING_PARAMETER, value, mode="add")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置呼吸参数时出错: {e}")
                return # 出错则中断本次呼吸
                
            # 控制更新频率
            next_step_time = min(current_time + 0.016, end_time)  # 约60fps
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # 2. 呼气阶段（从BREATHING_MAX_VALUE减少到BREATHING_MIN_VALUE）
        logger.info(f"开始呼气 ({BREATHING_MAX_VALUE} -> {BREATHING_MIN_VALUE})")
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + BREATHING_EXHALE_DURATION
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / BREATHING_EXHALE_DURATION)
            
            # 使用ease_in_sine计算当前值（反向）
            delta = (BREATHING_MAX_VALUE - BREATHING_MIN_VALUE) * (1.0 - ease_in_out_sine(progress))
            value = BREATHING_MIN_VALUE + delta
            
            # 使用add模式设置参数
            try:
                await plugin.set_parameter_value(BREATHING_PARAMETER, value, mode="add")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置呼吸参数时出错: {e}")
                return # 出错则中断本次呼吸
                
            # 控制更新频率
            next_step_time = min(current_time + 0.016, end_time)  # 约60fps
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                
    except Exception as e:
        logger.error(f"执行呼吸周期时发生意外错误: {e}")
        logger.error(traceback.format_exc())
        
    return True  # 返回True表示呼吸周期完成

# --- 呼吸任务 ---
async def breathing_task(plugin: VTSPlugin):
    """持续运行呼吸效果的任务"""
    global breathing_active
    breathing_active = True
    
    logger.info("开始呼吸效果...")
    
    try:
        while not shutdown_event.is_set() and breathing_active:
            # 执行一次完整的呼吸周期
            success = await breathing_cycle(plugin)
            if not success:
                # 如果呼吸周期执行失败，暂停一下再继续
                await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info("呼吸任务被取消")
    except Exception as e:
        logger.error(f"呼吸任务发生错误: {e}")
        logger.error(traceback.format_exc())
    finally:
        breathing_active = False
        logger.info("呼吸效果已停止")

# --- 身体摇摆效果逻辑 ---
async def body_swing_cycle(plugin: VTSPlugin):
    """执行一次随机的身体摇摆周期，从上一个位置直接过渡到下一个位置"""
    global current_x_position, current_z_position, current_eye_x_position, current_eye_y_position
    logger.info("开始随机身体摇摆周期")
    
    try:
        # 随机生成本次摇摆的参数
        # 随机生成摇摆的目标值 - 避免生成与当前位置太接近的值
        while True:
            # 直接在指定范围内随机生成新的目标位置
            new_x_target = random.uniform(BODY_SWING_X_MIN, BODY_SWING_X_MAX)
            new_z_target = random.uniform(BODY_SWING_Z_MIN, BODY_SWING_Z_MAX)
            
            # 确保新位置与当前位置有足够差异
            x_diff = abs(new_x_target - current_x_position)
            z_diff = abs(new_z_target - current_z_position)
            
            # 修改为更合理的终止条件: 只要位置变化足够大，则接受这个新位置
            if x_diff > 5.0 or z_diff > 7.5:
                break
            
            # 防止极端情况下的死循环，尝试10次后强制跳出
            if '_loop_count' not in locals():
                _loop_count = 0
            _loop_count += 1
            if _loop_count >= 10:
                logger.warning("随机位置生成10次仍未满足条件，强制接受当前生成的位置")
                break
        
        # 基于身体摇摆位置计算眼睛的目标位置
        if EYE_FOLLOW_ENABLED:
            # 计算眼睛X轴位置：将身体X轴范围映射到眼睛X轴范围
            # 归一化当前X位置在身体摇摆范围内的比例
            body_x_range = BODY_SWING_X_MAX - BODY_SWING_X_MIN
            x_norm = (new_x_target - BODY_SWING_X_MIN) / body_x_range if body_x_range != 0 else 0
            
            # 映射到眼睛X轴范围
            eye_x_range = EYE_X_MAX_RANGE - EYE_X_MIN_RANGE
            new_eye_x_target = EYE_X_MIN_RANGE + x_norm * eye_x_range
            
            # 计算眼睛Y轴位置：将身体Z轴范围映射到眼睛Y轴范围
            body_z_range = BODY_SWING_Z_MAX - BODY_SWING_Z_MIN
            z_norm = (new_z_target - BODY_SWING_Z_MIN) / body_z_range if body_z_range != 0 else 0
            
            # 映射到眼睛Y轴范围
            eye_y_range = EYE_Y_MAX_RANGE - EYE_Y_MIN_RANGE
            new_eye_y_target = EYE_Y_MIN_RANGE + z_norm * eye_y_range
            
            logger.info(f"眼睛跟随: 当前=({current_eye_x_position:.2f}, {current_eye_y_position:.2f}), "
                    f"目标=({new_eye_x_target:.2f}, {new_eye_y_target:.2f})")
        
        # 随机生成摇摆持续时间
        swing_duration = random.uniform(BODY_SWING_MIN_DURATION, BODY_SWING_MAX_DURATION)
        
        # 随机选择一种缓动函数
        easing_funcs = [
            ease_in_out_sine,
            ease_in_out_sine,    # 平滑流畅
            ease_in_out_quad,    # 稍慢开始结束，中间快
            ease_in_out_back,
        ]
        # 偏向于使用更自然的缓动函数
        weights = [0.5, 0.25 ,0.15 ,0.1]
        easing_func = random.choices(easing_funcs, weights=weights)[0]
        easing_name = easing_func.__name__
        
        logger.info(f"随机摇摆参数: 当前位置=({current_x_position:.2f}, {current_z_position:.2f}), "
                    f"目标=({new_x_target:.2f}, {new_z_target:.2f}), "
                    f"持续时间={swing_duration:.2f}s, 缓动函数={easing_name}")
        
        # 从当前位置到新目标位置的平滑过渡
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + swing_duration
        
        # 记录起始位置（当前位置）
        start_x = current_x_position
        start_z = current_z_position
        
        # 初始化眼睛位置变量（防止条件分支导致的未定义错误）
        start_eye_x = current_eye_x_position
        start_eye_y = current_eye_y_position
        
        # 记录眼睛起始位置
        if EYE_FOLLOW_ENABLED:
            start_eye_x = current_eye_x_position
            start_eye_y = current_eye_y_position
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / swing_duration)
            
            # 使用所选缓动函数计算当前值
            eased_progress = easing_func(progress)
            
            # 从起始位置平滑过渡到目标位置
            x_value = start_x + (new_x_target - start_x) * eased_progress
            z_value = start_z + (new_z_target - start_z) * eased_progress
        
            
            # 更新当前位置
            current_x_position = x_value
            current_z_position = z_value
            
            # 使用set模式设置绝对参数值
            try:
                await plugin.set_parameter_value(BODY_SWING_X_PARAMETER, x_value, mode="set")
                await plugin.set_parameter_value(BODY_SWING_Z_PARAMETER, z_value, mode="set")
                
                # 同步更新眼睛位置
                if EYE_FOLLOW_ENABLED:
                    # 计算眼睛当前位置
                    eye_x_value = start_eye_x + (new_eye_x_target - start_eye_x) * eased_progress
                    eye_y_value = start_eye_y + (new_eye_y_target - start_eye_y) * eased_progress
                    
                    # 更新眼睛当前位置
                    current_eye_x_position = eye_x_value
                    current_eye_y_position = eye_y_value
                    
                    # 设置眼睛参数
                    await plugin.set_parameter_value(EYE_LEFT_X_PARAMETER, eye_x_value, mode="set")
                    await plugin.set_parameter_value(EYE_RIGHT_X_PARAMETER, eye_x_value, mode="set")
                    await plugin.set_parameter_value(EYE_LEFT_Y_PARAMETER, eye_y_value, mode="set")
                    await plugin.set_parameter_value(EYE_RIGHT_Y_PARAMETER, eye_y_value, mode="set")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置身体摇摆参数时出错: {e}")
                return False # 出错则中断本次摇摆
                
            # 控制更新频率
            next_step_time = min(current_time + 0.033, end_time)  # 约30fps
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # 确保到达目标位置
        try:
            await plugin.set_parameter_value(BODY_SWING_X_PARAMETER, new_x_target, mode="set")
            await plugin.set_parameter_value(BODY_SWING_Z_PARAMETER, new_z_target, mode="set")
            current_x_position = new_x_target
            current_z_position = new_z_target
            
            # 确保眼睛到达目标位置
            if EYE_FOLLOW_ENABLED:
                await plugin.set_parameter_value(EYE_LEFT_X_PARAMETER, new_eye_x_target, mode="set")
                await plugin.set_parameter_value(EYE_RIGHT_X_PARAMETER, new_eye_x_target, mode="set")
                await plugin.set_parameter_value(EYE_LEFT_Y_PARAMETER, new_eye_y_target, mode="set")
                await plugin.set_parameter_value(EYE_RIGHT_Y_PARAMETER, new_eye_y_target, mode="set")
                current_eye_x_position = new_eye_x_target
                current_eye_y_position = new_eye_y_target
        except (APIError, ResponseError, ConnectionError) as e:
            logger.error(f"设置最终身体摇摆参数时出错: {e}")
                
    except Exception as e:
        logger.error(f"执行身体摇摆周期时发生意外错误: {e}")
        logger.error(traceback.format_exc())
        return False
        
    return True  # 返回True表示身体摇摆周期完成

# --- 身体摇摆任务 ---
async def body_swing_task(plugin: VTSPlugin):
    """持续运行身体摇摆效果的任务"""
    global body_swing_active
    body_swing_active = True
    
    logger.info("开始身体摇摆效果...")
    
    try:
        while not shutdown_event.is_set() and body_swing_active:
            # 执行一次完整的身体摇摆周期
            success = await body_swing_cycle(plugin)
            if not success:
                # 如果身体摇摆周期执行失败，暂停一下再继续
                await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info("身体摇摆任务被取消")
    except Exception as e:
        logger.error(f"身体摇摆任务发生错误: {e}")
        logger.error(traceback.format_exc())
    finally:
        body_swing_active = False
        logger.info("身体摇摆效果已停止")

# --- 嘴部表情逻辑 ---
async def mouth_expression_cycle(plugin: VTSPlugin):
    """执行一次随机的嘴部表情变化周期"""
    global current_mouth_smile, current_mouth_open
    logger.info("开始随机嘴部表情变化周期")
    
    try:
        # 随机生成本次表情变化的参数
        # 随机生成表情的目标值 - 避免生成与当前表情太接近的值
        while True:
            # 直接在指定范围内随机生成新的目标表情
            new_mouth_smile = random.uniform(MOUTH_SMILE_MIN, MOUTH_SMILE_MAX)
            
            # 随机决定是否张嘴（有70%概率保持嘴巴闭合或微开）
            if random.random() < 0.7:
                new_mouth_open = random.uniform(MOUTH_OPEN_MIN, MOUTH_OPEN_MIN + 0.2)
            else:
                new_mouth_open = random.uniform(MOUTH_OPEN_MIN + 0.2, MOUTH_OPEN_MAX)
            
            # 特殊处理：当嘴巴张开较大时，微笑值会影响嘴型
            # 如果嘴巴张开较大，适当增加微笑值的变化范围
            if new_mouth_open > 0.3:
                # 根据开口程度调整微笑程度，避免奇怪表情
                if random.random() < 0.5:  # 50%概率产生微笑配合开口
                    new_mouth_smile = random.uniform(0.3, MOUTH_SMILE_MAX)
                else:  # 50%概率产生小o型或大O型嘴
                    new_mouth_smile = random.uniform(MOUTH_SMILE_MIN, 0.3)
            
            # 确保新表情与当前表情有足够差异
            smile_diff = abs(new_mouth_smile - current_mouth_smile)
            open_diff = abs(new_mouth_open - current_mouth_open)
            
            # 确保表情变化既不太小也不太大，使变化更自然
            # 微笑值最小变化0.1，最大变化0.5
            # 开口值最小变化0.1，最大变化0.4
            if ((smile_diff > 0.1 and smile_diff < 0.5) or
                (open_diff > 0.1 and open_diff < 0.4)):
                break
            
            # 防止极端情况下的死循环，尝试10次后强制跳出
            if '_loop_count' not in locals():
                _loop_count = 0
            _loop_count += 1
            if _loop_count >= 10:
                logger.warning("随机表情生成10次仍未满足条件，强制接受当前生成的表情")
                break
        
        # 随机生成表情变化持续时间
        # 延长持续时间，使表情变化更加平滑、缓慢
        expression_duration = random.uniform(MOUTH_CHANGE_MIN_DURATION, MOUTH_CHANGE_MAX_DURATION)
        
        # 随机选择一种缓动函数
        easing_funcs = [
            ease_in_out_sine,
            ease_in_out_sine,    # 平滑流畅
            ease_in_out_quad,    # 稍慢开始结束，中间快
            ease_in_out_back,
        ]
        # 偏向于使用更自然的缓动函数
        weights = [0.5, 0.25 ,0.15 ,0.1]
        easing_func = random.choices(easing_funcs, weights=weights)[0]
        easing_name = easing_func.__name__
        
        logger.info(f"随机表情参数: 当前表情=(微笑:{current_mouth_smile:.2f}, 开口:{current_mouth_open:.2f}), "
                    f"目标=(微笑:{new_mouth_smile:.2f}, 开口:{new_mouth_open:.2f}), "
                    f"持续时间={expression_duration:.2f}s, 缓动函数={easing_name}")
        
        # 从当前表情到新目标表情的平滑过渡
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + expression_duration
        
        # 记录起始表情（当前表情）
        start_mouth_smile = current_mouth_smile
        start_mouth_open = current_mouth_open
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / expression_duration)
            
            # 使用所选缓动函数计算当前值
            eased_progress = easing_func(progress)
            
            # 从起始表情平滑过渡到目标表情
            smile_value = start_mouth_smile + (new_mouth_smile - start_mouth_smile) * eased_progress
            open_value = start_mouth_open + (new_mouth_open - start_mouth_open) * eased_progress
        
            # 更新当前表情
            current_mouth_smile = smile_value
            current_mouth_open = open_value
            
            # 使用set模式设置绝对参数值
            try:
                await plugin.set_parameter_value(MOUTH_SMILE_PARAMETER, smile_value, mode="set")
                await plugin.set_parameter_value(MOUTH_OPEN_PARAMETER, open_value, mode="set")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置嘴部表情参数时出错: {e}")
                return False # 出错则中断本次表情变化
                
            # 控制更新频率
            next_step_time = min(current_time + 0.033, end_time)  # 约30fps
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # 确保到达目标表情
        try:
            await plugin.set_parameter_value(MOUTH_SMILE_PARAMETER, new_mouth_smile, mode="set")
            await plugin.set_parameter_value(MOUTH_OPEN_PARAMETER, new_mouth_open, mode="set")
            current_mouth_smile = new_mouth_smile
            current_mouth_open = new_mouth_open
        except (APIError, ResponseError, ConnectionError) as e:
            logger.error(f"设置最终嘴部表情参数时出错: {e}")
                
    except Exception as e:
        logger.error(f"执行嘴部表情变化周期时发生意外错误: {e}")
        logger.error(traceback.format_exc())
        return False
        
    return True  # 返回True表示嘴部表情变化周期完成

# --- 嘴部表情任务 ---
async def mouth_expression_task(plugin: VTSPlugin):
    """持续运行嘴部表情变化的任务"""
    global mouth_expression_active
    mouth_expression_active = True
    
    logger.info("开始嘴部表情变化效果...")
    
    try:
        while not shutdown_event.is_set() and mouth_expression_active:
            # 执行一次完整的嘴部表情变化周期
            success = await mouth_expression_cycle(plugin)
            if not success:
                # 如果嘴部表情变化周期执行失败，暂停一下再继续
                await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info("嘴部表情任务被取消")
    except Exception as e:
        logger.error(f"嘴部表情任务发生错误: {e}")
        logger.error(traceback.format_exc())
    finally:
        mouth_expression_active = False
        logger.info("嘴部表情变化效果已停止")

# --- 眨眼任务 ---
async def blink_task(plugin: VTSPlugin):
    """持续运行眨眼效果的任务"""
    global blink_active
    blink_active = True
    
    logger.info("开始自动眨眼效果...")
    
    try:
        while not shutdown_event.is_set() and blink_active:
            # 随机等待一段时间
            wait_time = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
            logger.info(f"下次眨眼等待: {wait_time:.2f} 秒")
            
            try:
                # 使用 asyncio.wait_for 来允许在等待期间被中断
                await asyncio.wait_for(asyncio.sleep(wait_time), timeout=wait_time + 1)
            except asyncio.TimeoutError:
                pass # 正常等待完成
                
            if shutdown_event.is_set() or not blink_active:
                break # 检查是否在等待期间收到了关闭信号
            
            # 执行眨眼
            logger.info("执行眨眼...")
            await blink_cycle(
                plugin=plugin,
                close_duration=CLOSE_DURATION,
                open_duration=OPEN_DURATION,
                closed_hold=CLOSED_HOLD
            )
    except asyncio.CancelledError:
        logger.info("眨眼任务被取消")
    except Exception as e:
        logger.error(f"眨眼任务发生错误: {e}")
        logger.error(traceback.format_exc())
    finally:
        blink_active = False
        logger.info("眨眼效果已停止")

# --- 主循环 ---
async def run_loop():
    """运行眨眼插件的主循环"""
    global plugin, current_x_position, current_z_position, current_eye_x_position, current_eye_y_position
    global current_mouth_smile, current_mouth_open
    
    # 重置全局变量
    current_x_position = 0.0
    current_z_position = 0.0
    current_eye_x_position = 0.0
    current_eye_y_position = 0.0
    current_mouth_smile = 0.0  # 初始设为中性表情
    current_mouth_open = 0.0   # 初始设为闭嘴
    
    # 初始化任务对象
    blink_task_obj = None
    breathing_task_obj = None
    body_swing_task_obj = None
    mouth_expression_task_obj = None
    
    plugin = VTSPlugin(
        plugin_name=PLUGIN_NAME,
        plugin_developer=PLUGIN_DEVELOPER,
        endpoint=DEFAULT_VTS_ENDPOINT
    )

    logger.info(f"尝试连接到 VTube Studio: {DEFAULT_VTS_ENDPOINT}")

    try:
        # 连接与认证，但可随时中断
        authentication_done = asyncio.Event()
        authentication_result = [False]  # 使用列表来存储结果，这样可以在回调中修改
        
        async def auth_process():
            try:
                # 尝试连接和认证
                if plugin is not None:
                    result = await plugin.connect_and_authenticate()
                    authentication_result[0] = result
                else:
                    logger.error("插件未初始化，无法进行认证")
                    return False
            except Exception as e:
                logger.error(f"认证过程出错: {e}")
            finally:
                # 无论认证成功与否，都标记为完成
                authentication_done.set()
        
        # 启动认证过程
        auth_task = asyncio.create_task(auth_process())
        
        # 等待认证完成或收到关闭信号
        while not authentication_done.is_set() and not shutdown_event.is_set():
            # 同时等待两个事件，但最多等待0.1秒
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        authentication_done.wait(),
                        shutdown_event.wait()
                    ),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                # 超时继续循环检查
                pass
        
        # 如果收到关闭信号且认证未完成，取消认证任务
        if shutdown_event.is_set() and not authentication_done.is_set():
            logger.info("在认证过程中收到关闭信号，中止连接...")
            auth_task.cancel()
            try:
                await auth_task
            except asyncio.CancelledError:
                pass
            return
        
        # 获取认证结果
        authenticated = authentication_result[0]
        if not authenticated:
            logger.critical("认证失败，请检查 VTube Studio API 设置或令牌文件。")
            return
        
        global start_parameters
        start_parameters = await plugin.get_available_parameters()
        

        logger.info("认证成功！开始自动眨眼循环。")
        logger.info(f"眨眼间隔: {MIN_INTERVAL:.2f}-{MAX_INTERVAL:.2f} 秒")
        logger.info(f"动画速度: 闭眼={CLOSE_DURATION:.2f}s, 睁眼={OPEN_DURATION:.2f}s, 闭合保持={CLOSED_HOLD:.2f}s")
        
        # 启动眨眼任务
        blink_task_obj = asyncio.create_task(blink_task(plugin))
        
        # 启动呼吸任务
        breathing_task_obj = None
        if BREATHING_ENABLED:
            logger.info(f"启动呼吸效果 (参数: {BREATHING_PARAMETER}, 范围: {BREATHING_MIN_VALUE} ~ {BREATHING_MAX_VALUE})")
            logger.info(f"呼吸周期: 吸气={BREATHING_INHALE_DURATION:.1f}s, 呼气={BREATHING_EXHALE_DURATION:.1f}s")
            breathing_task_obj = asyncio.create_task(breathing_task(plugin))
            
        # 启动身体摇摆任务
        body_swing_task_obj = None
        if BODY_SWING_ENABLED:
            logger.info(f"启动随机身体摇摆效果 (X参数: {BODY_SWING_X_PARAMETER}, 范围: {BODY_SWING_X_MIN} ~ {BODY_SWING_X_MAX})")
            logger.info(f"启动随机上肢旋转效果 (Z参数: {BODY_SWING_Z_PARAMETER}, 范围: {BODY_SWING_Z_MIN} ~ {BODY_SWING_Z_MAX})")
            body_swing_task_obj = asyncio.create_task(body_swing_task(plugin))
            
        # 启动嘴部表情任务
        mouth_expression_task_obj = None
        if MOUTH_EXPRESSION_ENABLED:
            logger.info(f"启动随机嘴部表情效果 (微笑参数: {MOUTH_SMILE_PARAMETER}, 范围: {MOUTH_SMILE_MIN} ~ {MOUTH_SMILE_MAX})")
            logger.info(f"启动随机嘴部开合效果 (开口参数: {MOUTH_OPEN_PARAMETER}, 范围: {MOUTH_OPEN_MIN} ~ {MOUTH_OPEN_MAX})")
            mouth_expression_task_obj = asyncio.create_task(mouth_expression_task(plugin))

        # 等待关闭信号
        while not shutdown_event.is_set():
            await asyncio.sleep(0.5)  # 定期检查关闭信号

    except ConnectionError as e:
        logger.critical(f"无法连接到 VTube Studio: {e}")
    except AuthenticationError as e:
        logger.critical(f"认证过程中出错: {e}")
    except VTSException as e:
        logger.error(f"VTube Studio API 错误: {e}")
    except asyncio.CancelledError:
        logger.info("主任务被取消，正在关闭...")
    except Exception as e:
        logger.error(f"运行眨眼循环时发生未处理的异常: {e}")
        logger.error(traceback.format_exc())
    finally:
        # 清理操作
        logger.info("开始清理...")
        
        # 取消眨眼任务
        if blink_task_obj and not blink_task_obj.done():
            logger.info("正在停止眨眼效果...")
            blink_task_obj.cancel()
            try:
                await blink_task_obj  # 等待任务真正结束
            except asyncio.CancelledError:
                pass
        
        # 取消呼吸任务
        if breathing_task_obj and not breathing_task_obj.done():
            logger.info("正在停止呼吸效果...")
            breathing_task_obj.cancel()
            try:
                await breathing_task_obj  # 等待任务真正结束
            except asyncio.CancelledError:
                pass
                
        # 取消身体摇摆任务
        if body_swing_task_obj and not body_swing_task_obj.done():
            logger.info("正在停止身体摇摆效果...")
            body_swing_task_obj.cancel()
            try:
                await body_swing_task_obj  # 等待任务真正结束
            except asyncio.CancelledError:
                pass
                
        # 取消嘴部表情任务
        if mouth_expression_task_obj and not mouth_expression_task_obj.done():
            logger.info("正在停止嘴部表情效果...")
            mouth_expression_task_obj.cancel()
            try:
                await mouth_expression_task_obj  # 等待任务真正结束
            except asyncio.CancelledError:
                pass
            
        if plugin and plugin.client.is_authenticated:
            logger.info("尝试将模型参数恢复为初始状态...")
            try:
                # 优先尝试设置参数，即使断开连接可能失败
                await plugin.set_parameter_value("EyeOpenLeft", 1.0, mode="set")
                await plugin.set_parameter_value("EyeOpenRight", 1.0, mode="set")
                
                # 重置呼吸参数
                await plugin.set_parameter_value(BREATHING_PARAMETER, 0.0, mode="set")
                
                # 重置身体摇摆参数
                await plugin.set_parameter_value(BODY_SWING_X_PARAMETER, 0.0, mode="set")
                await plugin.set_parameter_value(BODY_SWING_Z_PARAMETER, 0.0, mode="set")
                
                # 重置眼睛位置参数
                if EYE_FOLLOW_ENABLED:
                    await plugin.set_parameter_value(EYE_LEFT_X_PARAMETER, 0.0, mode="set")
                    await plugin.set_parameter_value(EYE_RIGHT_X_PARAMETER, 0.0, mode="set")
                    await plugin.set_parameter_value(EYE_LEFT_Y_PARAMETER, 0.0, mode="set")
                    await plugin.set_parameter_value(EYE_RIGHT_Y_PARAMETER, 0.0, mode="set")
                    
                # 重置嘴部表情参数
                await plugin.set_parameter_value(MOUTH_SMILE_PARAMETER, 0.0, mode="set")
                await plugin.set_parameter_value(MOUTH_OPEN_PARAMETER, 0.0, mode="set")
                
                current_x_position = 0.0
                current_z_position = 0.0
                current_eye_x_position = 0.0
                current_eye_y_position = 0.0
                current_mouth_smile = 0.0
                current_mouth_open = 0.0
                
                logger.info("模型参数已尝试恢复。")
            except Exception as e_set:
                # 记录错误，但不阻塞关闭流程
                logger.warning(f"恢复模型参数时出错（可能已断开连接）: {e_set}")
        
        if plugin:
            await plugin.disconnect()
            logger.info("与 VTube Studio 的连接已断开。")
        
        logger.info("插件已关闭。")

# --- 信号处理 ---
def handle_signal(sig, frame):
    """处理 SIGINT (Ctrl+C) 和 SIGTERM"""
    logger.info(f"收到信号 {signal.Signals(sig).name}, 准备关闭...")
    # 设置事件，让主循环优雅退出
    shutdown_event.set()

# --- 入口点 ---
if __name__ == "__main__":
    # 设置信号处理
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("启动自动眨眼插件...")

    # 运行主异步函数
    main_task = None
    try:
        main_task = asyncio.run(run_loop())
    except KeyboardInterrupt:
        logger.info("程序被 Ctrl+C 强制退出")
    except asyncio.CancelledError:
        logger.info("主事件循环被取消。")
    finally:
        if main_task and not main_task.done():
            logger.info("尝试取消主任务...")
            main_task.cancel()
            # 给予一点时间处理取消
            # asyncio.run 会自动处理任务的最终完成或取消
        logger.info("插件进程结束。") 