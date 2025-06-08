# VTS Face Control Plugin

一个为 VTube Studio 开发的插件，旨在通过自动化、富有表现力的动画和直播互动功能，让您的虚拟形象栩栩如生。

## ✨ 功能特性

- **自动空闲动画**:
  - **眨眼**: 模拟自然的眨眼动作。
  - **呼吸**: 实现平滑的呼吸起伏效果。
  - **身体摇摆**: 身体和头部会进行自然的轻微摇摆。
  - **嘴部表情**: 自动切换微笑和嘴型，让表情更丰富。
- **Bilibili 直播集成**:
  - 监听直播间弹幕和消息。
  - 可配置通过弹幕触发与LLM模型的交互。
- **RPG 风格语音合成**:
  - 根据输入文本，播放经典 RPG 游戏风格的 "打字机" 音效。
  - 在屏幕上显示对应的字幕。
- **Web API 控制**:
  - 提供 WebSocket API，允许其他程序触发动作，如播放动画、改变表情、说话等。

## 🚀 部署指南

### 1. 先决条件

在开始之前，请确保您的系统已安装以下软件：

- [Python 3.10](https://www.python.org/downloads/) 或更高版本
- [Poetry](https://python-poetry.org/docs/#installation) (Python 依赖管理工具)
- [VTube Studio](https://store.steampowered.com/app/1325860/VTube_Studio/)
  - **重要**: 请在 VTube Studio 中启动 API，并允许插件连接。

### 2. 安装与配置

**步骤 1: 克隆项目**

```bash
git clone <your-repository-url>
cd vts-face-control-plugin
```

**步骤 2: 安装依赖项**

本项目使用 Poetry 管理依赖。运行以下命令安装所有必需的包：

```bash
poetry install
```

**步骤 3: 配置文件**

项目的主要配置文件位于 `data/configs/vts_model_control.yaml`。首次运行时会自动创建。您需要根据自己的需求修改此文件。

- **`PLUGIN.VTS_ENDPOINT`**: VTube Studio API 的地址，通常保持默认 `ws://localhost:8001` 即可。
- **`BILIBILI_CONFIGS`**: Bilibili 直播相关的配置。
  - `LIVE_ROOM_ID`: 您的B站直播间ID。
  - `SESSDATA`, `BILI_JCT`, `BUVID3`: 您的B站身份凭证 (Cookie)。
    - **如何获取 Cookie**: 您可以参考此文档来获取必要的 Cookie 信息：[bilibili-api 获取身份凭证](https://nemo2011.github.io/bilibili-api/#/get-credential)
- **`SPEECH_SYNTHESIS`**: 语音合成配置。
  - `AUDIO_FILE_PATH`: 用于 RPG 风格语音的音频文件。**注意：此文件必须是 `.wav` 格式。**
  - 您可以替换为您自己的 `.wav` 文件，并更新此路径。

**步骤 4: 放置资源文件**

- **音频**: 其他需要播放的音效文件 (如动画音效) 也必须是 `.wav` 格式，并应放置在 `data/resources/audios/` 目录下。
- **字体**: 字幕所使用的字体文件放置在 `data/resources/fonts/` 目录下，您可以在配置中修改 `FONT_PATH`。

### 3. 运行应用

完成上述配置后，通过以下命令启动插件：

```bash
poetry run python vts_model_control/main.py
```

**首次运行**:
首次运行时，您需要在 VTube Studio 中点击弹出的窗口，授权本插件的连接请求。授权后，插件会自动保存 token 用于未来的连接。

程序启动后，您会看到日志输出，显示已成功连接到 VTube Studio 并启动了各项动画控制器。

## 🔌 API 使用

本插件提供 WebSocket 端点，用于高级用户和开发者进行外部控制。

- `ws://<host>:<port>/ws/animate_control`: 用于发送控制指令 (如播放动画、设置表情等)。
- `ws://<host>:<port>/ws/subtitles`: 用于接收字幕广播。
- `ws://<host>:<port>/ws/danmaku`: 用于接收 B 站弹幕广播。

默认 `host` 为 `0.0.0.0`，`port` 为 `8080`。

## 📁 项目结构

```
.
├── data/
│   ├── configs/              # 配置文件
│   └── resources/            # 资源文件 (音频, 字体等)
├── vts_model_control/
│   ├── animations/           # 各种自动化动画控制器
│   ├── clients/              # 外部服务客户端 (如B站直播)
│   ├── services/             # 核心服务 (VTS插件, 动作调度等)
│   ├── main.py               # FastAPI 应用主入口
│   └── ...                   # 其他模块
├── pyproject.toml            # 项目依赖 (Poetry)
└── README.md                 # 本文档
```
