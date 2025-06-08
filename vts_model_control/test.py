import asyncio
import json

import websockets


async def test_animation_control():
    uri = "ws://localhost:8080/ws/animate_control"
    
    async with websockets.connect(uri) as websocket:
        print("已连接到WebSocket服务器")
        expression = {
            "type": "emotion",
            "data": {

            }
        }
        await websocket.send(json.dumps(expression))
        response = await websocket.recv()
        print(response)
        audio = {
            "type": "sound_play",
            "data": {

            }
        }
        await websocket.send(json.dumps(audio))
        response = await websocket.recv()
        print(response)
        # 第二阶段：发送眨眼动画
        say_animation = {
            "type": "say",
            "data": {
                "text": ["你好呀", "今天天气不错呢！"],
                "speed": [10.0,  9.0],
            },
        }
        await websocket.send(json.dumps(say_animation))
        response = await websocket.recv()
        eye_animation = {
            "type": "animation",
            "data": {
                "parameter": "EyeOpenRight",
                "target": 1.0,
                "duration": 0.2,
                "delay": 0.0,
                "easing": "in_out_sine",
            },
        }
        await websocket.send(json.dumps(eye_animation))
        response = await websocket.recv()
        eye_animation = {
            "type": "animation",
            "data": {
                "parameter": "EyeOpenLeft",
                "target": 1.0,
                "duration": 0.2,
                "delay": 0.0,
                "easing": "in_out_sine",
            },
        }
        await websocket.send(json.dumps(eye_animation))
        response = await websocket.recv()
        eye_animation = {
            "type": "animation",
            "data": {
                "parameter": "EyeOpenLeft",
                "target": 0.0,
                "duration": 0.2,
                "delay": 0.2,
                "easing": "in_out_sine",
            },
        }
        await websocket.send(json.dumps(eye_animation))
        response = await websocket.recv()
        eye_animation = {
            "type": "animation",
            "data": {
                "parameter": "EyeOpenLeft",
                "target": 0.0,
                "duration": 1,
                "delay": 0.4,
                "easing": "in_out_sine",
            },
        }
        await websocket.send(json.dumps(eye_animation))
        response = await websocket.recv()
        audio_animation = {
            "type": "sound_play",
            "data": {
                "path": "罐头笑声.wav",
                "duration": 2,
                "volume": 1.0,
                "speed": 1.0,
                "delay": 0.0,
            },
        }
        await websocket.send(json.dumps(audio_animation))
        response = await websocket.recv()
        # 第五阶段：执行所有动作
        execute_command = {
            "type": "execute",
            "data": {
                "loop": 0,
            },
        }
        await websocket.send(json.dumps(execute_command))
        response = await websocket.recv()
if __name__ == "__main__":
    asyncio.run(test_animation_control())