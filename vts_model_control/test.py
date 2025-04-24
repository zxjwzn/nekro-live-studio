import requests
import json

# 发送动画请求
animation = {
  "actions": [
    {
      "parameter": "EyeOpenLeft",
      "from": 1.0,
      "to": 0.0,
      "duration": 0.15,
      "easing": "outSine"
    },
    {
      "parameter": "MouthOpen",
      "to": 0.7,
      "duration": 0.5,
      "delay": 0.1,
      "easing": "inOutQuad"
    }
  ],
  "loop": 3
}

response = requests.post("http://localhost:8080/animation", json=animation)
print(response.json())