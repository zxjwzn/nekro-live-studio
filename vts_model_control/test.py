import requests
import json

# 发送动画请求
animation = {
  "actions": [
    {
      "parameter": "EyeOpenLeft",
      "from": 1.0,
      "to": 0.0,
      "duration": 0.3,
      "startTime": 0.0,
      "easing": "out_sine"
    },
    {
      "parameter": "MouthSmile",
      "from": 0.0,
      "to": 0.7,
      "duration": 0.5,
      "startTime": 0.35,
      "easing": "in_out_quad"
    }
  ],
  "loop": 0
}

response = requests.post("http://localhost:8080/animation", json=animation)
print(response.json())