import requests
import json

# 发送动画请求
animation = {
  "actions": [
    {
      "type":"say",
      "text":["你好!","我喜欢你"],
      "speeds":[3,20],
      "startTime": 0.0
    },
    {
      "type":"animation",
      "parameter": "EyeOpenLeft",
      "from": 1.0,
      "to": 0.0,
      "duration": 0.15,
      "startTime": 0.0,
      "easing": "outSine"
    },
    {
      "type":"animation",
      "parameter": "MouthOpen",
      "to": 0.7,
      "duration": 0.5,
      "startTime": 0.1,
      "easing": "inOutQuad"
    },
    {
      "type": "emotion",
      "name": "2脸红.exp3.json",
      "duration": 1,
      "startTime": 0.0
    }
  ],
  "loop": 0
}

response = requests.post("http://localhost:8080/animation", json=animation)
print(response.json())