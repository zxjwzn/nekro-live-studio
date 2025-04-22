import asyncio
from typing import Dict
from .easing import ease_in_out_sine
from .blink import BlinkAnimation
from .breathing import BreathingAnimation
from .body_movement import BodySwingAnimation
from .mouth_expression import MouthExpressionAnimation

class AnimationManager:
    """动画管理器：初始化、启动、停止所有动画，并平滑恢复参数"""
    def __init__(self, plugin, config, logger):
        self.plugin = plugin
        self.config = config
        self.logger = logger
        self.animations = []
        self.initial_values: Dict[str, float] = {}
        # 平滑恢复时长，可从配置扩展
        self.restore_duration = getattr(config.plugin, 'RESTORE_DURATION', 1.0)

    def initialize(self):
        """根据配置实例化需要的动画模块"""
        # 眨眼
        blink_cfg = self.config.blink
        if blink_cfg.ENABLED:
            self.animations.append(BlinkAnimation(self.plugin, blink_cfg, self.logger))
        # 呼吸
        breathing_cfg = self.config.breathing
        if breathing_cfg.ENABLED:
            self.animations.append(BreathingAnimation(self.plugin, breathing_cfg, self.logger))
        # 身体摇摆及眼睛跟随
        if self.config.body_swing.ENABLED:
            self.animations.append(BodySwingAnimation(self.plugin, self.config, self.logger))
        # 嘴部表情
        mouth_cfg = self.config.mouth_expression
        if mouth_cfg.ENABLED:
            self.animations.append(MouthExpressionAnimation(self.plugin, mouth_cfg, self.logger))

    async def store_initial_parameters(self):
        """保存将被动画控制的参数的初始值"""
        params = []
        # 眨眼参数
        if self.config.blink.ENABLED:
            params += [self.config.blink.LEFT_PARAMETER, self.config.blink.RIGHT_PARAMETER]
        # 呼吸参数
        if self.config.breathing.ENABLED:
            params.append(self.config.breathing.PARAMETER)
        # 身体摇摆参数
        if self.config.body_swing.ENABLED:
            params += [self.config.body_swing.X_PARAMETER, self.config.body_swing.Z_PARAMETER]
            if self.config.eye_follow.ENABLED:
                params += [
                    self.config.eye_follow.LEFT_X_PARAMETER,
                    self.config.eye_follow.RIGHT_X_PARAMETER,
                    self.config.eye_follow.LEFT_Y_PARAMETER,
                    self.config.eye_follow.RIGHT_Y_PARAMETER,
                ]
        # 嘴部表情参数
        if self.config.mouth_expression.ENABLED:
            params += [self.config.mouth_expression.SMILE_PARAMETER, self.config.mouth_expression.OPEN_PARAMETER]
        # 获取并记录
        for name in params:
            try:
                data = await self.plugin.get_parameter_value(name)
                value = data.get('value', 0.0)
                self.initial_values[name] = value
                self.logger.debug(f"记录初始参数 {name}={value}")
            except Exception as e:
                self.logger.warning(f"获取初始参数 {name} 出错: {e}")

    async def start_all(self):
        """启动所有动画"""
        for anim in self.animations:
            anim.start()

    async def stop_all(self):
        """停止所有动画"""
        # 为每个动画创建单独的任务并设置超时
        per_anim_timeout = 1.0  # 每个动画最多等待1秒
        
        async def stop_with_timeout(anim, index):
            try:
                await asyncio.wait_for(anim.stop(), timeout=per_anim_timeout)
                return True, index, None
            except asyncio.TimeoutError:
                self.logger.warning(f"动画 {index} 停止超时")
                return False, index, "超时"
            except Exception as e:
                self.logger.warning(f"动画 {index} 停止出错: {e}")
                return False, index, str(e)
        
        tasks = [stop_with_timeout(anim, i) for i, anim in enumerate(self.animations)]
        
        # 等待所有任务完成或超时
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for result in results:
            if isinstance(result, tuple) and len(result) == 3:
                success, index, error = result
                if not success:
                    self.logger.warning(f"动画 {index} 未能正常停止: {error}")

    async def restore_parameters(self):
        """平滑恢复参数至初始值，避免突变"""
        if not self.initial_values:
            return
        self.logger.info("平滑恢复初始参数...")
        # 获取当前值
        current = {}
        for name, orig in self.initial_values.items():
            try:
                data = await self.plugin.get_parameter_value(name)
                current[name] = data.get('value', orig)
            except Exception:
                current[name] = orig
        # 平滑过渡
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + self.restore_duration
        while True:
            now = asyncio.get_event_loop().time()
            if now >= end_time:
                break
            t = (now - start_time) / self.restore_duration
            eased = ease_in_out_sine(t)
            tasks = []
            for name, orig in self.initial_values.items():
                start_val = current.get(name, orig)
                target = orig
                val = start_val + (target - start_val) * eased
                tasks.append(self.plugin.set_parameter_value(name, val, mode='set'))
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.016)
        # 最终设置
        tasks = [self.plugin.set_parameter_value(name, orig, mode='set') for name, orig in self.initial_values.items()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("初始参数恢复完成") 