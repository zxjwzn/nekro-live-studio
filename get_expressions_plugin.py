"""
VTubeStudio 表情列表获取插件

此插件用于获取当前加载模型的所有可用表情列表，并展示相关信息。
"""

import asyncio
import logging
import sys
from typing import Dict, Any, List

from vts_client import VTSPlugin

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("expressions_plugin")

class ExpressionsPlugin:
    """VTubeStudio 表情列表获取插件"""
    
    def __init__(self):
        """初始化插件"""
        self.plugin = VTSPlugin(
            plugin_name="表情列表获取插件",
            plugin_developer="Claude用户",
            endpoint="ws://localhost:8001"
        )
        
    async def connect(self) -> bool:
        """连接到VTubeStudio并认证"""
        try:
            await self.plugin.connect_and_authenticate()
            logger.info("成功连接并认证VTubeStudio")
            return True
        except Exception as e:
            logger.error(f"连接或认证VTubeStudio失败: {str(e)}")
            return False
            
    async def get_current_model_info(self) -> Dict[str, Any]:
        """获取当前加载的模型信息"""
        try:
            model_info = await self.plugin.get_current_model()
            if not model_info.get("modelLoaded", False):
                logger.warning("当前没有加载模型")
                return {}
            logger.info(f"当前模型: {model_info.get('modelName', '未知')}")
            return model_info
        except Exception as e:
            logger.error(f"获取当前模型信息失败: {str(e)}")
            return {}
            
    async def get_expressions(self) -> List[Dict[str, Any]]:
        """获取当前模型的所有表情列表"""
        try:
            expressions = await self.plugin.get_expressions()
            logger.info(f"成功获取{len(expressions)}个表情")
            return expressions
        except Exception as e:
            logger.error(f"获取表情列表失败: {str(e)}")
            return []
            
    def format_expression_info(self, expression: Dict[str, Any]) -> str:
        """格式化表情信息为可读文本"""
        name = expression.get("name", "未知")
        file = expression.get("file", "未知")
        active = "已激活" if expression.get("active", False) else "未激活"
        return f"表情: {name} - 文件: {file} - 状态: {active}"
            
    async def print_expression_list(self) -> None:
        """打印当前模型的表情列表"""
        # 获取当前模型信息
        model_info = await self.get_current_model_info()
        if not model_info:
            return
            
        # 获取表情列表
        expressions = await self.get_expressions()
        if not expressions:
            logger.info("当前模型没有可用的表情")
            return
            
        # 打印表情信息
        print(f"\n当前模型 '{model_info.get('modelName')}' 的表情列表:")
        print("-" * 60)
        for i, exp in enumerate(expressions, 1):
            print(f"{i}. {self.format_expression_info(exp)}")
        print("-" * 60)
        
    async def activate_expression(self, expression_file: str, active: bool = True) -> bool:
        """激活或停用指定表情"""
        try:
            await self.plugin.activate_expression(expression_file, active)
            status = "激活" if active else "停用"
            logger.info(f"成功{status}表情: {expression_file}")
            return True
        except Exception as e:
            logger.error(f"操作表情失败: {str(e)}")
            return False
            
    async def interactive_mode(self) -> None:
        """交互模式，允许用户激活/停用表情"""
        while True:
            await self.print_expression_list()
            print("\n选项:")
            print("1. 激活表情")
            print("2. 停用表情") 
            print("3. 刷新列表")
            print("4. 退出")
            
            choice = input("\n请选择操作 [1-4]: ")
            
            if choice == "1" or choice == "2":
                is_activate = (choice == "1")
                exp_num = input("请输入表情编号: ")
                try:
                    idx = int(exp_num) - 1
                    expressions = await self.get_expressions()
                    if 0 <= idx < len(expressions):
                        file = expressions[idx].get("file", "")
                        if file:
                            await self.activate_expression(file, is_activate)
                        else:
                            print("无效的表情文件")
                    else:
                        print("无效的编号")
                except ValueError:
                    print("请输入有效的数字")
            elif choice == "3":
                continue
            elif choice == "4":
                break
            else:
                print("无效选择，请重试")
            
            input("\n按Enter继续...")
            
    async def run(self) -> None:
        """运行插件"""
        try:
            # 连接到VTubeStudio
            if not await self.connect():
                return
                
            # 运行交互模式
            await self.interactive_mode()
                
        finally:
            # 断开连接
            await self.plugin.disconnect()
            logger.info("已断开与VTubeStudio的连接")

async def main():
    """主函数"""
    plugin = ExpressionsPlugin()
    await plugin.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已终止")
    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
        sys.exit(1) 