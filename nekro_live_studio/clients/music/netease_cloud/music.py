import asyncio
import contextlib
import time
from pathlib import Path
from typing import Any, Optional

import anyio
import httpx
import qrcode
from pyncm import (
    DumpSessionAsString,
    GetCurrentSession,
    LoadSessionFromString,
    SetCurrentSession,
)
from pyncm.apis import cloudsearch as search
from pyncm.apis.login import (
    GetCurrentLoginStatus,
    LoginFailedException,
    LoginQrcodeCheck,
    LoginQrcodeUnikey,
    LoginViaAnonymousAccount,
    LoginViaCellphone,
    LoginViaEmail,
    SetSendRegisterVerifcationCodeViaCellphone,
    WriteLoginInfo,
)
from pyncm.apis.track import GetTrackAudio

from ....configs.config import config, save_config
from ....utils.logger import logger
from .utils import NCMResponseError, ncm_request, run_sync


# 代码借鉴自 https://github.com/lgc-NB2Dev/nonebot-plugin-multincm
class NeteaseCloudMusicClient:
    """网易云音乐客户端, 用于登录和获取音乐信息"""

    def __init__(self):
        self._running = False

    async def _sms_login(self, phone: str, country_code: int = 86):
        timeout = 60

        while True:
            await ncm_request(
                SetSendRegisterVerifcationCodeViaCellphone,
                phone,
                country_code,
            )
            last_send_time = time.time()
            logger.success(
                f"已发送验证码到 +{country_code} {'*' * (len(phone) - 3)}{phone[-3:]}",
            )

            while True:
                captcha = input("> 请输入验证码，留空直接回车代表重发: ").strip()
                if not captcha:
                    if (time_passed := (time.time() - last_send_time)) >= timeout:
                        break
                    logger.warning(f"请等待 {timeout - time_passed:.0f} 秒后再重发")
                    continue

                try:
                    await ncm_request(
                        LoginViaCellphone,
                        phone=phone,
                        ctcode=country_code,
                        captcha=captcha,
                    )
                except LoginFailedException as e:
                    data: dict[str, Any] = e.args[0]
                    if data.get("code") != 503:
                        raise
                    logger.error("验证码错误，请重新输入")
                else:
                    return

    async def _phone_login(
        self,
        phone: str,
        password: str,
        country_code: int = 86,
    ):
        """通过手机号和密码登录"""
        await run_sync(LoginViaCellphone)(
            ctcode=country_code,
            phone=phone,
            password=password,
        )

    async def _email_login(
        self,
        email: str,
        password: str,
    ):
        """通过邮箱和密码登录"""
        await run_sync(LoginViaEmail)(
            email=email,
            password=password,
        )

    async def _qrcode_login(self):
        """通过二维码登录"""

        async def wait_scan(uni_key: str) -> bool:
            last_status: Optional[int] = None
            login_start_time = time.time()
            while time.time() - login_start_time < 180:  # 3分钟超时
                await asyncio.sleep(2)
                try:
                    await ncm_request(LoginQrcodeCheck, uni_key)
                except NCMResponseError as e:
                    code = e.code
                    if code != last_status:
                        last_status = code
                        extra_tip = f" (用户：{e.data.get('nickname')})" if code == 802 else ""
                        logger.info(f"当前二维码状态：[{code}] {e.message}{extra_tip}")
                    elif code == 800:
                        logger.warning("二维码已过期")
                        return False
                    elif code == 803:
                        logger.info("授权成功")
                        return True
                    elif code and (code >= 1000):
                        raise
                    else:
                        raise
            logger.error("二维码登录超时")
            return False

        while True:
            uni_key: str = (await ncm_request(LoginQrcodeUnikey))["unikey"]
            url = f"https://music.163.com/login?codekey={uni_key}"
            qr = qrcode.QRCode()  # type: ignore
            qr.add_data(url)

            logger.info("请使用网易云音乐 APP 扫描下方二维码完成登录 (3分钟内):")
            qr.print_ascii()

            qr_img_filename = "ncm_qrcode.png"
            qr_img_path = Path.cwd() / qr_img_filename
            try:
                qr.make_image().save(str(qr_img_path))
                logger.info(
                    f"二维码图片已保存至应用根目录的 {qr_img_filename} 文件，如终端中二维码无法扫描可使用",
                )
            except Exception as e:
                logger.warning(f"保存二维码图片失败: {e}")

            logger.info("或使用下方 URL 生成二维码扫描登录：")
            logger.info(url)

            try:
                scan_res = await wait_scan(uni_key)
            finally:
                with contextlib.suppress(Exception):
                    qr_img_path.unlink(missing_ok=True)

            if scan_res:
                return  # 登录成功, 退出循环
            logger.info("二维码已过期或登录超时，将生成新的二维码。")

    async def _anonymous_login(self):
        """游客登录"""
        await ncm_request(LoginViaAnonymousAccount)

    async def _validate_login(self) -> bool:
        """验证当前登录状态"""
        ok = False
        try:
            ret = await ncm_request(GetCurrentLoginStatus)
            ok = bool(ret.get("account"))
            if ok:
                WriteLoginInfo(ret, GetCurrentSession())
        except Exception:
            logger.warning("获取登录状态失败", exc_info=True)

        return ok

    async def search_song(self, keyword: str, limit: int = 10) -> list:
        """模糊搜索歌曲"""
        logger.info(f"正在搜索歌曲: {keyword}")
        songs: list = []
        try:
            result = await ncm_request(
                search.GetSearchResult,
                keyword,
                stype=search.SONG,
                limit=limit,
            )
            songs = result.get("result", {}).get("songs", [])
            logger.success(f"成功搜索到 {len(songs)} 首歌曲")
        except Exception:
            logger.exception(f"搜索歌曲“{keyword}”时发生错误")
        return songs

    async def download_song(self, song_id: int, song_name: str, path: Path = Path("data/temp/")):
        """下载歌曲到 data/temp 目录"""
        temp_dir = path
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 获取下载链接
            audio_info = await ncm_request(GetTrackAudio, [song_id], bitrate=config.NCM.BITRATE)
            if not audio_info.get("data") or not isinstance(audio_info["data"], list) or not audio_info["data"][0].get("url"):
                logger.error(f"获取歌曲 {song_id} 的下载链接失败: {audio_info}")
                return

            download_url = audio_info["data"][0]["url"]
            file_extension = download_url.split("?")[0].split(".")[-1]
            file_path = temp_dir / f"{song_name}.{file_extension}"

            logger.info(f"正在下载歌曲: {song_name} (ID: {song_id})")
            async with httpx.AsyncClient() as client, client.stream(
                "GET", download_url, timeout=60, follow_redirects=True,
            ) as response:
                response.raise_for_status()
                # total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0
                with Path(file_path).open("wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # percentage = (
                        #     f"{(downloaded_size / total_size) * 100:.2f}%"
                        #     if total_size > 0
                        #     else f"{downloaded_size // 1024} KB"
                        # )
                        # logger.info(
                        #     f"\r下载进度: {percentage}",
                        #     end="",
                        # )
            logger.success(f"歌曲已成功下载到: {file_path}")

        except httpx.HTTPStatusError as e:
            logger.error(f"下载歌曲时网络错误: {e.response.status_code}")
        except Exception:
            logger.exception(f"下载歌曲 {song_name} (ID: {song_id}) 时发生错误")

    async def _do_login(self):
        """执行登录流程"""
        using_cached_session = False
        ncm_config = config.NCM

        if ncm_config.ANONYMOUS:
            logger.info("使用游客身份登录")
            await self._anonymous_login()

        elif ncm_config.SESSION_DATA:
            logger.info("检测到缓存会话, 正在加载...")
            SetCurrentSession(LoadSessionFromString(ncm_config.SESSION_DATA))
            using_cached_session = True

        elif ncm_config.PHONE:
            if ncm_config.PASSWORD:
                logger.info("使用手机号与密码登录")
                await self._phone_login(ncm_config.PHONE, ncm_config.PASSWORD)
            else:
                logger.info("使用手机号登录")
                await self._sms_login(ncm_config.PHONE)

        elif ncm_config.EMAIL and ncm_config.PASSWORD:
            logger.info("使用邮箱与密码登录")
            await self._email_login(ncm_config.EMAIL, ncm_config.PASSWORD)

        else:
            if ncm_config.PHONE and not ncm_config.PASSWORD:
                logger.warning("提供了手机号但未提供密码, 请配置密码或使用二维码登录。")
            if ncm_config.EMAIL and not ncm_config.PASSWORD:
                logger.warning("提供了邮箱但未提供密码, 请配置密码或使用二维码登录。")
            logger.info("将使用二维码登录")
            await self._qrcode_login()

        if not await self._validate_login():
            if using_cached_session:
                ncm_config.SESSION_DATA = ""
                logger.warning("缓存会话已失效, 已清除。请重新登录。")
                await self._do_login()  # 尝试重新走完整登录流程
            else:
                logger.error("网易云音乐登录失败。")
            return

        session = GetCurrentSession()
        if ncm_config.ANONYMOUS:
            logger.success("游客登录成功")
        else:
            if not using_cached_session:
                ncm_config.SESSION_DATA = DumpSessionAsString(session)
            logger.success(
                f"登录成功，欢迎您，{session.nickname} [{session.uid}]",
            )

    async def start(self):
        """启动网易云音乐客户端并登录"""
        if not config.NCM.ENABLED:
            logger.info("网易云音乐功能未在配置中启用。")
            return

        if self._running:
            logger.warning("网易云音乐客户端已在运行中。")
            return

        self._running = True
        logger.info("正在启动网易云音乐客户端...")

        try:
            if GetCurrentSession().logged_in and await self._validate_login():
                session = GetCurrentSession()
                logger.info(
                    f"检测到已存在的有效会话, 将跳过登录。欢迎, {session.nickname} [{session.uid}]",
                )
                return

            await self._do_login()
        except LoginFailedException as e:
            data: dict[str, Any] = e.args[0]
            logger.error(f"登录失败: {data.get('message', '未知错误')}")
        except Exception:
            logger.exception("网易云音乐登录时发生未知错误")
        finally:
            self._running = False

    async def stop(self):
        """停止网易云音乐客户端"""
        self._running = False   
        logger.info("网易云音乐客户端已停止")


netease_cloud_music_client = NeteaseCloudMusicClient()
