# VTubeStudio 面部控制插件

一个功能强大的VTubeStudio插件，允许通过外部API控制Live2D模型的面部动作和表情。

## 功能特点

- **面部参数控制**：通过API注入面部追踪参数，实现类似摄像头面部捕捉的效果
- **表情控制**：激活或停用模型的表情
- **外部API接口**：提供HTTP REST API，允许其他程序通过简单的请求控制模型
- **双重参数获取机制**：同时支持跟踪参数和Live2D参数
- **参数映射系统**：自动在Live2D参数和跟踪参数之间转换
- **健壮的错误处理**：自动重连、详细日志和备用方案

## 安装

### 前提条件

- Python 3.7+
- VTubeStudio 已安装并运行
- 在VTubeStudio中启用了插件API访问

### 安装步骤

1. 克隆或下载本仓库

2. 安装依赖：
```bash
pip install websockets aiohttp
```

3. 运行插件：
```bash
python vts_face_control_improved.py
```

4. 调试模式启动（获取更详细的日志）：
```bash
python vts_face_control_improved.py --debug
```

## 使用方法

### 基本使用

1. 启动VTubeStudio并加载一个模型
2. 启动插件
3. 通过HTTP API控制模型

### 命令行参数

```
usage: vts_face_control_improved.py [-h] [--vts-url VTS_URL] [--api-port API_PORT] [--debug]

VTubeStudio面部控制插件

optional arguments:
  -h, --help           显示帮助信息并退出
  --vts-url VTS_URL    VTubeStudio WebSocket URL (默认: ws://localhost:8001)
  --api-port API_PORT  外部API服务器端口 (默认: 8080)
  --debug              启用调试日志
```

### API使用示例

#### 设置面部参数

```bash
# 使用跟踪参数名
curl -X POST http://localhost:8080/parameter -H "Content-Type: application/json" -d '{"id":"FaceAngleX", "value":0.5}'

# 使用Live2D参数名（会自动映射）
curl -X POST http://localhost:8080/parameter -H "Content-Type: application/json" -d '{"id":"ParamAngleX", "value":0.5}'
```

#### 激活表情

```bash
curl -X POST http://localhost:8080/expression -H "Content-Type: application/json" -d '{"file":"happy.exp3.json", "active":true}'
```

#### 获取参数列表

```bash
curl http://localhost:8080/parameters
```

### 使用Python

```python
import requests
import json

# 设置单个参数
response = requests.post(
    "http://localhost:8080/parameter",
    json={"id": "FaceAngleX", "value": 0.5}
)
print(response.json())

# 设置多个参数
response = requests.post(
    "http://localhost:8080/parameters",
    json={
        "parameters": [
            {"id": "FaceAngleX", "value": 0.5},
            {"id": "MouthOpenY", "value": 0.7}
        ]
    }
)
print(response.json())

# 激活表情
response = requests.post(
    "http://localhost:8080/expression",
    json={"file": "happy.exp3.json", "active": True}
)
print(response.json())
```

### 使用JavaScript

```javascript
// 设置单个参数
fetch('http://localhost:8080/parameter', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        id: 'FaceAngleX',
        value: 0.5
    })
})
.then(response => response.json())
.then(data => console.log(data));

// 激活表情
fetch('http://localhost:8080/expression', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        file: 'happy.exp3.json',
        active: true
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

## 集成示例

### 与面部追踪软件集成

```python
import cv2
import requests
import numpy as np
import mediapipe as mp

# 初始化MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 打开摄像头
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, image = cap.read()
    if not success:
        continue
        
    # 转换为RGB并处理
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image_rgb)
    
    if results.multi_face_landmarks:
        face_landmarks = results.multi_face_landmarks[0]
        
        # 计算面部角度（简化示例）
        # 实际应用中需要更复杂的计算
        nose_tip = face_landmarks.landmark[4]
        left_eye = face_landmarks.landmark[33]
        right_eye = face_landmarks.landmark[263]
        
        # 计算水平角度
        face_angle_x = (nose_tip.x - 0.5) * 2
        
        # 发送到VTubeStudio插件
        requests.post(
            "http://localhost:8080/parameter",
            json={"id": "FaceAngleX", "value": face_angle_x}
        )
    
    # 显示图像
    cv2.imshow('MediaPipe Face Mesh', image)
    if cv2.waitKey(5) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
```

### 与游戏集成

```python
import pygame
import requests
import time

# 初始化Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("VTubeStudio控制示例")

# 主循环
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # 按键控制
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                # 向左转头
                requests.post(
                    "http://localhost:8080/parameter",
                    json={"id": "FaceAngleX", "value": -0.5}
                )
            elif event.key == pygame.K_RIGHT:
                # 向右转头
                requests.post(
                    "http://localhost:8080/parameter",
                    json={"id": "FaceAngleX", "value": 0.5}
                )
            elif event.key == pygame.K_UP:
                # 向上看
                requests.post(
                    "http://localhost:8080/parameter",
                    json={"id": "FaceAngleY", "value": -0.5}
                )
            elif event.key == pygame.K_DOWN:
                # 向下看
                requests.post(
                    "http://localhost:8080/parameter",
                    json={"id": "FaceAngleY", "value": 0.5}
                )
            elif event.key == pygame.K_SPACE:
                # 激活笑脸表情
                requests.post(
                    "http://localhost:8080/expression",
                    json={"file": "happy.exp3.json", "active": True}
                )
        
        # 释放按键时恢复默认状态
        if event.type == pygame.KEYUP:
            if event.key in [pygame.K_LEFT, pygame.K_RIGHT]:
                requests.post(
                    "http://localhost:8080/parameter",
                    json={"id": "FaceAngleX", "value": 0}
                )
            elif event.key in [pygame.K_UP, pygame.K_DOWN]:
                requests.post(
                    "http://localhost:8080/parameter",
                    json={"id": "FaceAngleY", "value": 0}
                )
            elif event.key == pygame.K_SPACE:
                requests.post(
                    "http://localhost:8080/expression",
                    json={"file": "happy.exp3.json", "active": False}
                )
    
    # 更新屏幕
    screen.fill((0, 0, 0))
    pygame.display.flip()
    time.sleep(0.01)

pygame.quit()
```

## 参数映射

插件支持在Live2D参数和跟踪参数之间进行自动映射。以下是主要的参数映射关系：

| Live2D参数 | 跟踪参数 |
|------------|----------|
| ParamAngleX | FaceAngleX |
| ParamAngleY | FaceAngleY |
| ParamAngleZ | FaceAngleZ |
| ParamEyeLOpen | EyeOpenLeft |
| ParamEyeROpen | EyeOpenRight |
| ParamEyeBallX | EyeLeftX |
| ParamEyeBallY | EyeLeftY |
| ParamMouthOpenY | MouthOpenY |
| ParamMouthForm | MouthSmile |
| ParamBrowLY | BrowLeftY |
| ParamBrowRY | BrowRightY |

## 常见问题

### 插件无法连接到VTubeStudio

- 确保VTubeStudio已启动
- 检查VTubeStudio设置中的WebSocket端口是否为8001
- 确保在VTubeStudio设置中启用了"允许插件API访问"
- 尝试重启VTubeStudio

### 参数列表为空

- 确保已加载模型
- 尝试使用调试模式启动插件以获取更详细的日志
- 插件会自动预加载常见参数，即使API返回空列表也能正常工作

### 表情控制不起作用

- 确保表情文件名正确，包括.exp3.json后缀
- 检查模型是否支持该表情
- 使用`/expressions`端点获取可用表情列表

## API文档

详细的API文档请参考[VTubeStudio 面部控制插件 API 文档.md](VTubeStudio 面部控制插件 API 文档.md)文件。

## 许可证

MIT

## 致谢

- [DenchiSoft](https://github.com/DenchiSoft) - VTubeStudio的开发者
- 所有VTubeStudio API文档的贡献者
