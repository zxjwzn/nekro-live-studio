import asyncio
import contextlib
import json
import re
import time
from typing import Optional

import qrcode
from bilibili_api import Credential, live, sync
from bilibili_api.exceptions.LiveException import LiveException
from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginEvents

from ....configs.config import config, save_config
from ....schemas.live import Danmaku
from ....services.websocket_manager import manager
from ....utils.logger import logger


class BilibiliLiveClient:
    """B站直播弹幕客户端"""

    def __init__(self):
        self.room_id = config.BILIBILI_LIVE.LIVE_ROOM_ID
        self.credential: Optional[Credential] = None
        self.live_danmaku: Optional[live.LiveDanmaku] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        # 触发器相关 - 队列模式
        self._danmaku_queue: list[Danmaku] = []
        self._first_message_time: float = 0.0
        self._check_timer_task: Optional[asyncio.Task] = None

    async def _login(self) -> Optional[Credential]:
        """尝试使用缓存凭据登录, 如果失败则尝试二维码登录"""
        bili_configs = config.BILIBILI_LIVE
        credential = None
        if bili_configs.SESSDATA and bili_configs.BILI_JCT:
            credential = Credential(
                sessdata=bili_configs.SESSDATA,
                bili_jct=bili_configs.BILI_JCT,
                buvid3=bili_configs.BUVID3,
                dedeuserid=bili_configs.DEDEUSERID or None,
                ac_time_value=bili_configs.AC_TIME_VALUE or None,
            )
            logger.info("检测到缓存凭据, 正在验证...")
            if not await credential.check_valid():
                logger.warning("缓存凭据无效, 将尝试扫码登录")
                credential = None
            else:
                logger.info("缓存凭据有效")
                if await credential.check_refresh():
                    logger.info("凭据即将过期, 正在尝试刷新...")
                    try:
                        await credential.refresh()
                        logger.info("凭据刷新成功")
                    except Exception:
                        logger.exception("凭据刷新失败, 将尝试扫码登录")
                        credential = None

        if credential:
            logger.info("使用缓存凭据登录成功")
            return credential

        logger.info("无有效缓存凭据, 将启动扫码登录...")
        new_credential = await self._qr_login()
        if new_credential:
            return new_credential
        return None

    async def _qr_login(self) -> Optional[Credential]:
        """通过二维码登录B站"""
        try:
            login_qrcode = QrCodeLogin()
            await login_qrcode.generate_qrcode()
            qr = qrcode.QRCode() # type: ignore
            qr.add_data(login_qrcode._QrCodeLogin__qr_link)  # type: ignore # noqa: SLF001
            logger.info("请在3分钟内扫描二维码登录:")
            qr.print_ascii()


            login_start_time = time.time()
            last_state = None
            logger.info("等待扫描二维码...")
            while time.time() - login_start_time < 180:  # 3分钟超时
                state = await login_qrcode.check_state()
                if state == QrCodeLoginEvents.DONE:
                    logger.info("扫码登录成功！")
                    return login_qrcode.get_credential()

                if state != last_state:
                    if state == QrCodeLoginEvents.TIMEOUT:
                        logger.warning("二维码已过期")
                        break  # exit loop
                    if state == QrCodeLoginEvents.CONF:
                        logger.info("二维码已扫描, 请在手机上确认登录...")

                    last_state = state

                await asyncio.sleep(2)

            logger.error("二维码登录超时")
            
        except Exception:
            logger.exception("二维码登录时发生错误")
            return None
        return None
    
    def _register_events(self):
        """注册直播事件处理函数"""
        if not self.live_danmaku:
            return

        @self.live_danmaku.on("DANMU_MSG")
        async def on_danmaku(event):
            try:
                danmaku_obj = self._parse_danmaku(event["data"])
                await self._add_to_queue(danmaku_obj)  # 添加到队列而不是直接转发
                logger.info(f"【弹幕】{danmaku_obj.username}: {danmaku_obj.text}")
            except Exception:
                logger.exception("处理弹幕消息时发生错误")

        @self.live_danmaku.on("INTERACT_WORD")
        async def on_interact(event):
            try:
                danmaku_obj = self._parse_interact_word(event["data"])
                if not danmaku_obj:
                    return
                logger.info(f"【互动】{danmaku_obj.text}")
                await manager.broadcast_json_to_path("/ws/danmaku", danmaku_obj.model_dump())
            except Exception:
                logger.exception("处理互动消息时发生错误")

        @self.live_danmaku.on("SUPER_CHAT_MESSAGE")
        async def on_super_chat(event):
            try:
                danmaku_obj = self._parse_super_chat(event["data"])
                logger.info(f"【SC】{danmaku_obj.text}")
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

        @self.live_danmaku.on("SEND_GIFT")
        async def on_gift(event):
            try:
                danmaku_obj = self._parse_gift(event["data"])
                logger.info(f"【礼物】{danmaku_obj.text}")
                await manager.broadcast_json_to_path(
                    "/ws/danmaku", danmaku_obj.model_dump(),
                )
            except Exception:
                logger.exception("处理礼物消息时发生错误")

    async def _add_to_queue(self, danmaku_obj: Danmaku) -> None:
        """将弹幕添加到队列并检查触发条件"""
        # 如果队列为空,启动计时器
        if not self._danmaku_queue:
            self._first_message_time = time.time()
            # 启动定时器检查
            if self._check_timer_task:
                self._check_timer_task.cancel()
            self._check_timer_task = asyncio.create_task(self._check_time_trigger())
        
        # 添加到队列
        self._danmaku_queue.append(danmaku_obj)
        
        # 检查条数触发
        if len(self._danmaku_queue) >= config.BILIBILI_LIVE.TRIGGER_COUNT:
            await self._trigger_and_flush()

    async def _check_time_trigger(self) -> None:
        """检查时间触发条件"""
        try:
            await asyncio.sleep(config.BILIBILI_LIVE.TRIGGER_TIME)
            if self._danmaku_queue:  # 如果队列中还有弹幕
                await self._trigger_and_flush()
        except asyncio.CancelledError:
            pass  # 任务被取消是正常的

    async def _trigger_and_flush(self) -> None:
        """触发转发并清空队列"""
        if not self._danmaku_queue:
            return
            
        # 取消定时器
        if self._check_timer_task:
            self._check_timer_task.cancel()
            self._check_timer_task = None
        
        # 批量转发弹幕，最后一条标记为触发
        for i, danmaku in enumerate(self._danmaku_queue):
            # 最后一条弹幕标记为触发
            if i == len(self._danmaku_queue) - 1:
                danmaku.is_trigger = True
            await manager.broadcast_json_to_path("/ws/danmaku", danmaku.model_dump())
            logger.debug(f"【转发弹幕】{danmaku.username}: {danmaku.text} (trigger: {danmaku.is_trigger})")
        
        # 清空队列和重置计时器
        logger.debug(f"触发转发完成，共转发 {len(self._danmaku_queue)} 条弹幕")
        self._danmaku_queue.clear()
        self._first_message_time = 0.0

    def _parse_gift(self, data: dict) -> Danmaku:
        gift_data = data["data"]
        username = gift_data["uname"]
        gift_name = gift_data["giftName"]
        num = gift_data["num"]
        return Danmaku(
            uid=str(gift_data["uid"]),
            username=username,
            text=f"{username} 赠送了 {num}个 {gift_name}",
            time=gift_data["timestamp"],
            is_system=True,
            is_trigger=True,  # 礼物默认直接触发
        )

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
        if self._running:
            logger.warning("B站直播客户端已在运行中")
            return

        if not self.room_id or self.room_id == "0":
            logger.warning("未配置B站直播间ID，直播监听功能未启用")
            return

        # 登录B站
        try:
            self.credential = await self._login()
            if self.credential:
                # 保存最新的凭据信息
                cookies = self.credential.get_cookies()
                config.BILIBILI_LIVE.SESSDATA = cookies["SESSDATA"]
                config.BILIBILI_LIVE.BUVID3 = cookies["buvid3"]
                config.BILIBILI_LIVE.BILI_JCT = cookies["bili_jct"]
                config.BILIBILI_LIVE.AC_TIME_VALUE = cookies.get("ac_time_value", "")
                logger.info("B站登录成功")
            else:
                logger.error("B站登录失败, 直播监听功能将不可用。")
                return
        except Exception:
            logger.exception("B站登录过程中发生未知错误")
            self.credential = None
            return

        # 创建 LiveDanmaku 实例并注册事件
        self.live_danmaku = live.LiveDanmaku(
            room_display_id=int(self.room_id),
            credential=self.credential,
            debug=config.LOG_LEVEL == "DEBUG",
        )
        self.live_danmaku.logger = logger  # type: ignore
        self._register_events()

        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
        logger.info("B站直播客户端已启动")

    async def stop(self):
        if not self._running:
            return

        self._running = False

        # 清理定时器任务
        if self._check_timer_task:
            self._check_timer_task.cancel()
            self._check_timer_task = None

        # 如果队列中还有弹幕，触发最后一次转发
        if self._danmaku_queue:
            await self._trigger_and_flush()

        if self.live_danmaku:
            await self.live_danmaku.disconnect()
            self.live_danmaku = None

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        logger.info("B站直播客户端已停止")

bilibili_live_client = BilibiliLiveClient()