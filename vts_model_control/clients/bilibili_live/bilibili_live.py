import asyncio
import contextlib
import json
import re
import time
from typing import Optional

from bilibili_api import Credential, live
from bilibili_api.exceptions.LiveException import LiveException
from configs.config import config
from schemas.bilibili_live import Danmaku
from utils.logger import logger

_websocket_manager = None


def get_websocket_manager():
    """延迟导入WebSocket管理器以避免循环依赖"""
    global _websocket_manager
    if _websocket_manager is None:
        try:
            from services.websocket_manager import manager

            _websocket_manager = manager
        except ImportError:
            logger.warning("无法导入WebSocket管理器，弹幕转发功能将不可用")
    return _websocket_manager


class BilibiliLiveClient:
    """B站直播弹幕客户端"""

    def __init__(self):
        self.room_id = config.BILIBILI_CONFIGS.LIVE_ROOM_ID
        self.credential: Optional[Credential] = None
        self.live_danmaku: Optional[live.LiveDanmaku] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        # 触发器相关
        self._message_count: int = 0
        self._first_message_time: float = 0.0

        if not self.room_id or self.room_id == "0":
            logger.warning("未配置B站直播间ID，直播监听功能未启用")
            return

        bili_configs = config.BILIBILI_CONFIGS
        if all([bili_configs.SESSDATA, bili_configs.BILI_JCT, bili_configs.BUVID3]):
            self.credential = Credential(
                sessdata=bili_configs.SESSDATA,
                bili_jct=bili_configs.BILI_JCT,
                buvid3=bili_configs.BUVID3,
                dedeuserid=bili_configs.DEDEUSERID or None,
                ac_time_value=bili_configs.AC_TIME_VALUE or None,
            )
            logger.info(f"已创建B站直播凭据, SESSDATA: ...{bili_configs.SESSDATA[-4:]}")
        else:
            logger.info("未提供完整的B站凭据, 将以游客身份连接")

        self.live_danmaku = live.LiveDanmaku(
            room_display_id=int(self.room_id),
            credential=self.credential,
            debug=config.LOG_LEVEL == "DEBUG",
        )
        self.live_danmaku.logger = logger # type: ignore
        self._register_events()

    def _register_events(self):
        """注册直播事件处理函数"""
        if not self.live_danmaku:
            return

        @self.live_danmaku.on("DANMU_MSG")
        async def on_danmaku(event):
            try:
                danmaku_obj = self._parse_danmaku(event["data"])
                danmaku_obj = self._handle_trigger_logic(danmaku_obj)  # 仅对普通弹幕应用触发逻辑
                logger.info(f"【弹幕】{danmaku_obj.username}: {danmaku_obj.text} (trigger: {danmaku_obj.is_trigger})")
                manager = get_websocket_manager()
                if manager:
                    await manager.broadcast_json_to_path("/ws/danmaku", danmaku_obj.model_dump())
            except Exception:
                logger.exception("处理弹幕消息时发生错误")

        @self.live_danmaku.on("INTERACT_WORD")
        async def on_interact(event):
            try:
                danmaku_obj = self._parse_interact_word(event["data"])
                if not danmaku_obj:
                    return
                logger.info(f"【互动】{danmaku_obj.text}")
                manager = get_websocket_manager()
                if manager:
                    await manager.broadcast_json_to_path("/ws/danmaku", danmaku_obj.model_dump())
            except Exception:
                logger.exception("处理互动消息时发生错误")

        @self.live_danmaku.on("SUPER_CHAT_MESSAGE")
        async def on_super_chat(event):
            try:
                danmaku_obj = self._parse_super_chat(event["data"])
                logger.info(f"【SC】{danmaku_obj.text}")
                manager = get_websocket_manager()
                if manager:
                    await manager.broadcast_json_to_path("/ws/danmaku", danmaku_obj.model_dump())
            except Exception:
                logger.exception("处理SC消息时发生错误")

        @self.live_danmaku.on("LIVE")
        async def on_live_start(_):
            logger.info(f"【系统】房间 {self.room_id} 的直播已开始")

        @self.live_danmaku.on("PREPARING")
        async def on_live_stop(_):
            logger.info(f"【系统】房间 {self.room_id} 的直播已结束")

        @self.live_danmaku.on("DISCONNECT")
        async def on_disconnect(event):
            logger.warning(f"【系统】与直播间 {self.room_id} 的连接已断开: {event}")

    def _handle_trigger_logic(self, danmaku_obj: Danmaku) -> Danmaku:
        """处理弹幕触发逻辑"""
        # 如果计时器未启动,则启动计时器
        if self._message_count == 0:
            self._first_message_time = time.time()
        
        self._message_count += 1

        trigger_by_count = self._message_count >= config.BILIBILI_CONFIGS.TRIGGER_COUNT
        time_elapsed = time.time() - self._first_message_time
        trigger_by_time = time_elapsed > config.BILIBILI_CONFIGS.TRIGGER_TIME and self._first_message_time != 0.0

        if trigger_by_count or trigger_by_time:
            danmaku_obj.is_trigger = True
            # 重置计数器和计时器
            self._message_count = 0
            self._first_message_time = 0.0
        
        return danmaku_obj

    def _parse_danmaku(self, data: dict) -> Danmaku:
        info = data["info"]
        text = info[1]
        user_info = info[2]
        uid = str(user_info[0])
        username = user_info[1]
        timestamp = info[9].get("ts", 0)
        urls = []

        extra_str = info[0][15].get("extra", "{}")
        extra_data = json.loads(extra_str)
        dm_type = extra_data.get("dm_type", 0)

        if dm_type == 0:  # 普通弹幕
            emots = extra_data.get("emots") or {}
            urls = [emot["url"] for emot in emots.values() if "url" in emot]
            text = re.sub(r"\\s+", " ", text).strip()
        elif dm_type == 1:  # 表情包
            emoticon_info = info[0][13]
            if isinstance(emoticon_info, dict) and "url" in emoticon_info:
                urls.append(emoticon_info["url"])

        return Danmaku(
            uid=uid,
            username=username,
            text=text,
            time=timestamp,
            url=urls,
        )

    def _parse_interact_word(self, data: dict) -> Optional[Danmaku]:
        interact_data = data["data"]
        msg_type = interact_data.get("msg_type")
        username = interact_data["uname"]
        uid = str(interact_data["uid"])
        timestamp = interact_data["timestamp"]

        text_map = {1: "进入了直播间", 2: "关注了主播", 3: "分享了直播间"}
        text_action = text_map.get(msg_type)
        if not text_action:
            return None

        return Danmaku(
            uid=uid,
            username=username,
            text=f"{username} {text_action}",
            time=timestamp,
            is_system=True,
            is_trigger=False,  # 互动消息永不触发
        )

    def _parse_super_chat(self, data: dict) -> Danmaku:
        sc_data = data["data"]
        uid = str(sc_data["uid"])
        username = sc_data["user_info"]["uname"]
        price = sc_data["price"]
        message = sc_data["message"]
        timestamp = sc_data["ts"]

        return Danmaku(
            uid=uid,
            username=username,
            text=f"{username} 的 {price}元 SC: {message}",
            time=timestamp,
            is_system=True,
            is_trigger=True,  # SC默认直接触发
        )

    async def _connection_loop(self):
        assert self.live_danmaku is not None
        while self._running:
            try:
                logger.info(f"正在尝试连接到B站直播间: {self.room_id}")
                await self.live_danmaku.connect()
                logger.info(f"成功连接到B站直播间: {self.room_id}, 开始监听...")
            except (asyncio.CancelledError, KeyboardInterrupt):
                logger.info("连接循环被手动取消")
                self._running = False
                break
            except LiveException as e:
                logger.warning(f"直播连接发生已知错误: {e}, 5秒后重连...")
            except Exception:
                logger.exception("连接B站直播间时发生未知错误, 5秒后重连...")

            if self._running:
                logger.info("直播间连接已断开, 5秒后将尝试重连...")
                await asyncio.sleep(5)

    async def start(self):
        if not self.live_danmaku:
            return
        if self._running:
            logger.warning("B站直播客户端已在运行中")
            return

        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
        logger.info("B站直播客户端已启动")

    async def stop(self):
        if not self._running:
            return

        self._running = False
        if self.live_danmaku:
            await self.live_danmaku.disconnect()

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        logger.info("B站直播客户端已停止")
