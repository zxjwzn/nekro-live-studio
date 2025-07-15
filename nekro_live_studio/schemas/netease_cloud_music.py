from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Artist(BaseModel):
    """歌手信息"""

    id: int = Field(..., description="歌手ID")
    name: str = Field(..., description="歌手名")
    tns: list[Any] = Field([], description="翻译名称列表")
    alias: list[str] = Field([], description="别名列表")
    alia: Optional[list[str]] = Field(None, description="专辑别名列表")


class Album(BaseModel):
    """专辑信息"""

    id: int = Field(..., description="专辑ID")
    name: str = Field(..., description="专辑名")
    pic_url: str = Field(..., alias="picUrl", description="专辑封面图片URL")
    tns: list[Any] = Field([], description="翻译名称列表")
    pic_str: Optional[str] = Field(None, alias="pic_str", description="专辑封面图片ID (字符串)")
    pic: int = Field(..., description="专辑封面图片ID (整数)")


class QualityInfo(BaseModel):
    """音质信息 (h/m/l/sq/hr)"""

    br: int = Field(..., description="比特率 (kbps)")
    fid: int = Field(..., description="文件ID")
    size: int = Field(..., description="文件大小 (字节)")
    vd: float = Field(..., description="音量增益 (dB)")
    sr: int = Field(..., description="采样率 (Hz)")


class OriginArtist(BaseModel):
    """原曲歌手信息"""

    id: int = Field(..., description="原曲歌手ID")
    name: str = Field(..., description="原曲歌手名")


class OriginAlbum(BaseModel):
    """原曲专辑信息"""

    id: int = Field(..., description="原曲专辑ID")
    name: str = Field(..., description="原曲专辑名")


class OriginSongSimpleData(BaseModel):
    """原曲简要信息 (通常用于翻唱歌曲)"""

    song_id: int = Field(..., alias="songId", description="原曲ID")
    name: str = Field(..., description="原曲名称")
    artists: list[OriginArtist] = Field(..., description="原曲歌手列表")
    album_meta: OriginAlbum = Field(..., alias="albumMeta", description="原曲专辑信息")


class FreeTrialPrivilege(BaseModel):
    """免费试听权限信息"""

    res_consumable: bool = Field(..., alias="resConsumable", description="资源是否可消费")
    user_consumable: bool = Field(..., alias="userConsumable", description="用户是否可消费")
    listen_type: Optional[Any] = Field(None, alias="listenType", description="收听类型")
    cannot_listen_reason: Optional[Any] = Field(None, alias="cannotListenReason", description="无法收听原因")
    play_reason: Optional[Any] = Field(None, alias="playReason", description="播放原因")
    free_limit_tag_type: Optional[Any] = Field(None, alias="freeLimitTagType", description="免费限制标签类型")


class ChargeInfo(BaseModel):
    """收费信息"""

    rate: int = Field(..., description="码率")
    charge_url: Optional[Any] = Field(None, alias="chargeUrl", description="收费URL")
    charge_message: Optional[Any] = Field(None, alias="chargeMessage", description="收费信息")
    charge_type: int = Field(..., alias="chargeType", description="收费类型")


class Privilege(BaseModel):
    """歌曲权限信息 (播放、下载等)"""

    id: int = Field(..., description="歌曲ID")
    fee: int = Field(..., description="费用类型 (0: 免费, 1: VIP, 4: 购买专辑, 8: 单曲购买)")
    payed: int = Field(..., description="是否已支付")
    st: int = Field(..., description="歌曲状态")
    pl: int = Field(..., description="可播放的最高比特率")
    dl: int = Field(..., description="可下载的最高比特率")
    sp: int = Field(..., description="播放权限")
    cp: int = Field(..., description="版权信息 (1为有版权)")
    subp: int = Field(..., description="订阅权限")
    cs: bool = Field(..., description="是否为云盘歌曲")
    maxbr: int = Field(..., description="最高比特率")
    fl: int = Field(..., description="可免费收听的最高比特率")
    toast: bool = Field(..., description="是否弹出toast提示")
    flag: int = Field(..., description="标志位")
    pre_sell: bool = Field(..., alias="preSell", description="是否为预售歌曲")
    play_maxbr: int = Field(..., alias="playMaxbr", description="可播放的最高比特率")
    download_maxbr: int = Field(..., alias="downloadMaxbr", description="可下载的最高比特率")
    max_br_level: str = Field(..., alias="maxBrLevel", description="最高比特率等级")
    play_max_br_level: str = Field(..., alias="playMaxBrLevel", description="播放最高比特率等级")
    download_max_br_level: str = Field(..., alias="downloadMaxBrLevel", description="下载最高比特率等级")
    pl_level: str = Field(..., alias="plLevel", description="播放音质等级")
    dl_level: str = Field(..., alias="dlLevel", description="下载音质等级")
    fl_level: str = Field(..., alias="flLevel", description="免费试听音质等级")
    rscl: Optional[Any] = Field(None, description="未知资源")
    free_trial_privilege: FreeTrialPrivilege = Field(..., alias="freeTrialPrivilege", description="免费试听权限")
    right_source: int = Field(..., alias="rightSource", description="版权来源")
    charge_info_list: list[ChargeInfo] = Field(..., alias="chargeInfoList", description="收费信息列表")
    code: int = Field(..., description="状态码")
    message: Optional[Any] = Field(None, description="消息")
    pl_levels: Optional[Any] = Field(None, alias="plLevels", description="播放音质等级列表")
    dl_levels: Optional[Any] = Field(None, alias="dlLevels", description="下载音质等级列表")
    ignore_cache: Optional[str] = Field(None, alias="ignoreCache", description="是否忽略缓存")


class Song(BaseModel):
    """网易云音乐歌曲信息模型"""

    id: int = Field(..., description="歌曲ID")
    name: str = Field(..., description="歌曲名称")
    pst: int = Field(..., description="付费标记")
    t: int = Field(..., description="标记")
    ar: list[Artist] = Field(..., description="歌手列表")
    alia: list[str] = Field([], description="歌曲别名列表")
    pop: float = Field(..., description="歌曲热度")
    st: int = Field(..., description="歌曲状态")
    rt: Optional[str] = Field(None, description="歌曲来源的电台信息")
    fee: int = Field(..., description="费用类型")
    v: int = Field(..., description="歌曲版本")
    crbt: Optional[Any] = Field(None, description="彩铃信息")
    cf: str = Field(..., description="未知")
    al: Album = Field(..., description="专辑信息")
    dt: int = Field(..., description="歌曲时长 (毫秒)")
    h: Optional[QualityInfo] = Field(None, description="高音质信息")
    m: Optional[QualityInfo] = Field(None, description="中音质信息")
    l: Optional[QualityInfo] = Field(None, description="低音质信息")  # noqa: E741
    sq: Optional[QualityInfo] = Field(None, description="无损音质信息")
    hr: Optional[QualityInfo] = Field(None, description="Hi-Res音质信息")
    a: Optional[Any] = Field(None, description="未知")
    cd: str = Field(..., description="CD编号")
    no: int = Field(..., description="歌曲在专辑中的序号")
    rt_url: Optional[Any] = Field(None, alias="rtUrl", description="未知URL")
    ftype: int = Field(..., description="文件类型")
    rt_urls: list[Any] = Field([], alias="rtUrls", description="未知URL列表")
    dj_id: int = Field(..., alias="djId", description="电台ID (如果来自电台)")
    copyright: int = Field(..., description="版权信息")
    s_id: int = Field(..., alias="s_id", description="歌曲来源ID")
    mark: int = Field(..., description="标记")
    origin_cover_type: int = Field(..., alias="originCoverType", description="原封面类型")
    origin_song_simple_data: Optional[OriginSongSimpleData] = Field(
        None, alias="originSongSimpleData", description="原曲简要信息 (用于翻唱歌曲)",
    )
    tag_pic_list: Optional[Any] = Field(None, alias="tagPicList", description="标签图片列表")
    resource_state: bool = Field(..., alias="resourceState", description="资源状态")
    version: int = Field(..., description="版本")
    song_jump_info: Optional[Any] = Field(None, alias="songJumpInfo", description="歌曲跳转信息")
    entertainment_tags: Optional[Any] = Field(None, alias="entertainmentTags", description="娱乐标签")
    single: int = Field(..., description="是否为单曲")
    no_copyright_rcmd: Optional[Any] = Field(None, alias="noCopyrightRcmd", description="无版权推荐")
    rtype: int = Field(..., description="未知类型")
    rurl: Optional[Any] = Field(None, description="未知URL")
    mst: int = Field(..., description="媒体流状态")
    cp: int = Field(..., description="版权提供方")
    mv: int = Field(..., description="MV ID (0表示没有)")

    publish_time: int = Field(..., alias="publishTime", description="发行时间 (毫秒时间戳)")
    privilege: Privilege = Field(..., description="歌曲权限信息")
