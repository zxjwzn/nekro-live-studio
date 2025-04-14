# VTubeStudio 面部控制插件 API 文档

本文档详细描述了VTubeStudio面部控制插件提供的所有API端点、参数和响应格式。

## 基本信息

- **基础URL**: `http://localhost:8080`
- **内容类型**: 所有请求和响应均使用JSON格式
- **认证**: 无需认证，仅限本地访问

## API端点概览

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 获取插件基本信息 |
| `/status` | GET | 获取插件和VTubeStudio状态 |
| `/parameters` | GET | 获取所有可用参数列表（合并后的） |
| `/live2d_parameters` | GET | 获取Live2D参数列表 |
| `/tracking_parameters` | GET | 获取跟踪参数列表 |
| `/expressions` | GET | 获取可用表情列表 |
| `/parameter` | POST | 设置单个参数值 |
| `/parameters` | POST | 设置多个参数值 |
| `/expression` | POST | 激活或停用表情 |

## 详细API说明

### 获取插件信息

获取插件的基本信息和可用API端点列表。

**请求**:
```
GET /
```

**响应**:
```json
{
  "name": "VTS面部控制插件",
  "author": "Manus",
  "status": "running",
  "authenticated": true,
  "model_loaded": true,
  "current_model": "模型名称",
  "endpoints": [
    {"path": "/", "method": "GET", "description": "获取插件信息"},
    {"path": "/status", "method": "GET", "description": "获取状态信息"},
    {"path": "/parameters", "method": "GET", "description": "获取所有可用参数列表"},
    {"path": "/live2d_parameters", "method": "GET", "description": "获取Live2D参数列表"},
    {"path": "/tracking_parameters", "method": "GET", "description": "获取跟踪参数列表"},
    {"path": "/expressions", "method": "GET", "description": "获取可用表情列表"},
    {"path": "/parameter", "method": "POST", "description": "设置单个参数值"},
    {"path": "/parameters", "method": "POST", "description": "设置多个参数值"},
    {"path": "/expression", "method": "POST", "description": "激活或停用表情"}
  ]
}
```

### 获取状态信息

获取插件和VTubeStudio的当前状态。

**请求**:
```
GET /status
```

**响应**:
```json
{
  "authenticated": true,
  "model_loaded": true,
  "current_model": "模型名称",
  "current_model_id": "模型ID",
  "tracking_parameter_count": 10,
  "live2d_parameter_count": 20,
  "available_parameter_count": 25,
  "expression_count": 5
}
```

### 获取所有可用参数列表

获取所有可用参数的列表，包括跟踪参数和Live2D参数。

**请求**:
```
GET /parameters
```

**响应**:
```json
{
  "parameters": [
    {
      "name": "FaceAngleX",
      "description": "面部水平旋转",
      "defaultValue": 0,
      "min": -30,
      "max": 30,
      "value": 0
    },
    {
      "name": "ParamAngleX",
      "description": "Live2D参数",
      "defaultValue": 0,
      "min": -30,
      "max": 30,
      "value": 0,
      "mappedTo": "FaceAngleX"
    },
    // 更多参数...
  ]
}
```

### 获取Live2D参数列表

仅获取Live2D参数的列表。

**请求**:
```
GET /live2d_parameters
```

**响应**:
```json
{
  "parameters": [
    {
      "name": "ParamAngleX",
      "value": 0,
      "min": -30,
      "max": 30,
      "defaultValue": 0
    },
    // 更多Live2D参数...
  ]
}
```

### 获取跟踪参数列表

仅获取跟踪参数的列表。

**请求**:
```
GET /tracking_parameters
```

**响应**:
```json
{
  "parameters": [
    {
      "name": "FaceAngleX",
      "value": 0,
      "min": -30,
      "max": 30,
      "defaultValue": 0
    },
    // 更多跟踪参数...
  ]
}
```

### 获取可用表情列表

获取当前模型可用的表情列表。

**请求**:
```
GET /expressions
```

**响应**:
```json
{
  "expressions": [
    {
      "name": "表情名称",
      "file": "表情文件名.exp3.json",
      "active": false
    },
    // 更多表情...
  ]
}
```

### 设置单个参数值

设置单个参数的值。

**请求**:
```
POST /parameter
Content-Type: application/json

{
  "id": "FaceAngleX",
  "value": 0.5,
  "weight": 1.0
}
```

**参数说明**:
- `id`: 参数ID，可以是跟踪参数名（如"FaceAngleX"）或Live2D参数名（如"ParamAngleX"）
- `value`: 参数值，通常在-1到1之间
- `weight`: 参数权重，0到1之间，可选，默认为1.0

**响应**:
```json
{
  "success": true
}
```

**错误响应**:
```json
{
  "error": "错误信息"
}
```

### 设置多个参数值

同时设置多个参数的值。

**请求**:
```
POST /parameters
Content-Type: application/json

{
  "parameters": [
    {
      "id": "FaceAngleX",
      "value": 0.5,
      "weight": 1.0
    },
    {
      "id": "FaceAngleY",
      "value": -0.3,
      "weight": 0.8
    }
    // 更多参数...
  ]
}
```

**响应**:
```json
{
  "success": true
}
```

**错误响应**:
```json
{
  "error": "错误信息"
}
```

### 激活或停用表情

激活或停用模型的表情。

**请求**:
```
POST /expression
Content-Type: application/json

{
  "file": "表情文件名.exp3.json",
  "active": true,
  "fade_time": 0.5
}
```

**参数说明**:
- `file`: 表情文件名，必须包含.exp3.json后缀
- `active`: 是否激活表情，true或false
- `fade_time`: 淡入淡出时间，单位为秒，可选，默认为0.5

**响应**:
```json
{
  "success": true
}
```

**错误响应**:
```json
{
  "error": "错误信息"
}
```

## 错误码

| 状态码 | 描述 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |

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

## 示例

### 使用curl设置面部参数

```bash
# 使用跟踪参数名
curl -X POST http://localhost:8080/parameter -H "Content-Type: application/json" -d '{"id":"FaceAngleX", "value":0.5}'

# 使用Live2D参数名（会自动映射）
curl -X POST http://localhost:8080/parameter -H "Content-Type: application/json" -d '{"id":"ParamAngleX", "value":0.5}'
```

### 使用curl激活表情

```bash
curl -X POST http://localhost:8080/expression -H "Content-Type: application/json" -d '{"file":"happy.exp3.json", "active":true, "fade_time":1.0}'
```

### 使用Python设置多个参数

```python
import requests
import json

url = "http://localhost:8080/parameters"
data = {
    "parameters": [
        {"id": "FaceAngleX", "value": 0.5},
        {"id": "MouthOpenY", "value": 0.7},
        {"id": "EyeOpenLeft", "value": 0.8}
    ]
}

response = requests.post(url, json=data)
print(response.json())
```

## 注意事项

1. 参数值通常应该在-1到1之间，但具体范围取决于参数的定义
2. 表情文件名必须包含.exp3.json后缀
3. 如果模型未加载，表情相关的API将返回错误
4. 插件会自动在Live2D参数和跟踪参数之间进行映射，用户可以使用任一种参数名
5. 如果参数列表为空，插件会自动预加载常见参数
