import asyncio
from bilibili_api import live, Credential
from utils.logger import logger
from configs.config import config
from api.schemas import Danmaku
import json
import re
from typing import Dict

# 使用延迟导入避免循环导入
_websocket_manager = None

def get_websocket_manager():
    """获取WebSocket管理器的延迟导入函数"""
    global _websocket_manager
    if _websocket_manager is None:
        try:
            from services.websocket_manager import manager
            _websocket_manager = manager
        except ImportError:
            logger.warning("无法导入WebSocket管理器，弹幕广播功能将不可用")
    return _websocket_manager

def parse_danmaku(danmaku_data: Dict) -> Danmaku:
    """
    解析B站弹幕消息，返回Danmaku模型
    支持解析所有表情并提取URL列表，从文本中去除表情内容
    """
    info = danmaku_data["data"]["info"]
    
    # 提取基本信息
    content = info[1]  # 弹幕内容
    user_info = info[2]
    username = user_info[1]
    uid = str(user_info[0])
    
    # 提取时间戳 (毫秒转秒)
    timestamp = info[9]["ts"] if info[9] else 0
    
    # 解析extra信息
    extra_str = info[0][15]["extra"]
    extra_data = json.loads(extra_str)
    dm_type = extra_data["dm_type"]
    
    # 初始化返回值
    text = content  # 先保留原始内容
    url_list = []  # 改为列表存储所有表情URL
    
    # 根据类型解析不同内容
    if dm_type == 0:
        if extra_data.get("emots"):
            # B站内置表情 - 提取所有表情的URL
            emots = extra_data["emots"]
            for emot_name, emot_info in emots.items():
                if "url" in emot_info:
                    url_list.append(emot_info["url"])
                    # 从文本中去除表情标签，如 [傲娇]
                    text = text.replace(emot_name, "")
        
        # 清理多余的空格
        text = re.sub(r'\s+', ' ', text.strip())
        
    elif dm_type == 1:
        # 收藏集表情
        emoticon_info = info[0][13]
        if isinstance(emoticon_info, dict) and "url" in emoticon_info:
            url_list.append(emoticon_info["url"])
            # 从文本中去除收藏集表情名称
            # 收藏集表情的名称通常是完整的content内容
            text = ""  # 收藏集表情通常没有额外文本，直接清空
    
    return Danmaku(
        uid=uid,
        username=username,
        text=text,
        time=timestamp,
        url=url_list,
        is_trigget=True,
    )

def parse_interact_word(interact_data: Dict) -> Danmaku:
    """
    解析B站用户进入直播间消息，返回Danmaku模型
    """
    data = interact_data["data"]["data"]
    
    # 提取基本信息
    username = data["uname"]
    uid = str(data["uid"])
    msg_type = data["msg_type"]
    timestamp = data["timestamp"]
    
    # 根据msg_type生成不同的文本内容
    if msg_type == 1:  # 进入直播间
        text = f"{username} 进入了直播间"
    elif msg_type == 2:  # 关注
        text = f"{username} 关注了主播"
    elif msg_type == 3:  # 分享直播间
        text = f"{username} 分享了直播间"
    else:
        text = f"{username} 与直播间互动"
    
    return Danmaku(
        uid=uid,
        username=username,
        text=text,
        time=timestamp,
        url=[],  # 用户交互消息没有表情，使用空列表
        is_system=True  # 标记为系统消息
    )

class BilibiliLiveClient:
    """B站直播弹幕客户端"""

    def __init__(self):
        """初始化B站直播客户端"""
        self.room_id = config.bilibili_configs.live_room_id
        self.credential = None
        self.live_danmaku = None
        self._running = False
        self._task = None

        # 检查必要的配置
        if self.room_id <= 0:
            logger.warning("未配置B站直播房间ID，直播弹幕监听功能未启用")
            return

        # 如果有凭据信息，则创建Credential对象
        if (
            config.bilibili_configs.sessdata
            and config.bilibili_configs.bili_jct
            and config.bilibili_configs.buvid3
        ):
            self.credential = Credential(
                sessdata=config.bilibili_configs.sessdata,
                bili_jct=config.bilibili_configs.bili_jct,
                buvid3=config.bilibili_configs.buvid3,
                dedeuserid=config.bilibili_configs.dedeuserid or None,
                ac_time_value=config.bilibili_configs.ac_time_value or None,
            )
            logger.info("已创建B站直播凭据")
        else:
            logger.info("未提供B站直播凭据，将以游客身份监听直播")

        # 创建直播弹幕监听实例
        self.live_danmaku = live.LiveDanmaku(
            room_display_id=self.room_id,
            credential=self.credential,
            debug=config.plugin.debug_mode,
        )

        # 注册事件处理函数
        self._register_events()

    def _register_events(self):
        """注册各种直播事件的处理函数"""
        if not self.live_danmaku:
            return

        @self.live_danmaku.on("DANMU_MSG")
        async def on_danmaku(event):
            """处理弹幕消息"""
            try:
                danmaku = parse_danmaku(event)
                logger.info(f"【弹幕】{danmaku.username}({danmaku.uid}): {danmaku.text}")
                
                # 通过WebSocket广播弹幕消息，只发送给/ws/danmaku路径的客户端
                websocket_manager = get_websocket_manager()
                if websocket_manager:
                    await websocket_manager.broadcast_json_to_path("danmaku", danmaku.model_dump())
            except Exception as e:
                logger.error(f"处理弹幕消息出错: {e}")

        @self.live_danmaku.on("INTERACT_WORD")
        async def on_interact_word(event):
            """处理用户进入直播间消息"""
            try:
                interact_danmaku = parse_interact_word(event)
                logger.info(f"【进入】{interact_danmaku.username}({interact_danmaku.uid}): {interact_danmaku.text}")
                
                # 通过WebSocket广播用户进入消息，只发送给/ws/danmaku路径的客户端
                websocket_manager = get_websocket_manager()
                if websocket_manager:
                    await websocket_manager.broadcast_json_to_path("danmaku", interact_danmaku.model_dump())
            except Exception as e:
                logger.error(f"处理用户进入消息出错: {e}")

        @self.live_danmaku.on("LIVE")
        async def on_live(event):
            """处理直播开始消息"""
            logger.info("【系统】直播开始")

        @self.live_danmaku.on("PREPARING")
        async def on_preparing(event):
            """处理直播准备中消息"""
            logger.info("【系统】直播准备中")

        @self.live_danmaku.on("ROOM_REAL_TIME_MESSAGE_UPDATE")
        async def on_room_update(event):
            """处理房间信息更新消息"""
            try:
                data = event["data"]["data"]
                fans = data.get("fans", 0)
                logger.debug(f"【更新】粉丝数: {fans}")
            except Exception as e:
                logger.error(f"处理房间更新消息出错: {e}")

        @self.live_danmaku.on("SUPER_CHAT_MESSAGE")
        async def on_super_chat(event):
            """处理醒目消息"""
            try:
                data = event["data"]["data"]
                username = data["user_info"]["uname"]
                price = data["price"]
                message = data["message"]
                logger.info(f"【SC】{username} ¥{price}: {message}")
            except Exception as e:
                logger.error(f"处理SC消息出错: {e}")

        @self.live_danmaku.on("DISCONNECT")
        async def on_disconnect(event):
            """处理断开连接消息"""
            logger.warning(f"【系统】直播间连接断开: {event}")
            # 尝试重新连接
            if self._running:
                logger.info("尝试重新连接直播间...")
                await asyncio.sleep(3)
                await self.connect()

    async def connect(self):
        """连接到直播间"""
        if not self.live_danmaku:
            logger.warning("直播弹幕监听未初始化，无法连接")
            return False

        try:
            self._running = True
            logger.info(f"正在连接到B站直播间 {self.room_id}...")
            await self.live_danmaku.connect()
            return True
        except Exception as e:
            logger.error(f"连接B站直播间失败: {e}")
            self._running = False
            return False

    async def disconnect(self):
        """断开直播间连接"""
        if not self.live_danmaku or not self._running:
            return

        try:
            self._running = False
            logger.info("正在断开B站直播间连接...")
            await self.live_danmaku.disconnect()
        except Exception as e:
            logger.error(f"断开B站直播间连接出错: {e}")

    async def start(self):
        """启动直播弹幕监听"""
        if not self.live_danmaku:
            logger.warning("直播弹幕监听未初始化，无法启动")
            return

        if self._task and not self._task.done():
            logger.warning("直播弹幕监听已在运行中")
            return

        # 创建连接任务
        self._task = asyncio.create_task(self.connect())
        logger.info("已启动B站直播弹幕监听")

    async def stop(self):
        """停止直播弹幕监听"""
        if not self._running:
            return

        await self.disconnect()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("已停止B站直播弹幕监听")


# 创建全局实例
bilibili_client = BilibiliLiveClient()


# 提供启动和停止方法
async def start_bilibili_live():
    """启动B站直播监听"""
    await bilibili_client.start()


async def stop_bilibili_live():
    """停止B站直播监听"""
    await bilibili_client.stop()
