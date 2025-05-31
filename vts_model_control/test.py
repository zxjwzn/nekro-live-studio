import asyncio
import websockets
import json

async def test_animation_control():
    uri = "ws://localhost:8080/ws/animate_control"
    
    async with websockets.connect(uri) as websocket:
        print("已连接到WebSocket服务器")
        
        # 第一阶段：发送说话行为
        say_action = {
            "type": "say",
            "data": {
                "text": ["你好!", "我喜欢你"],
                "speed": [3, 20],
                "delay": 0.0
            }
        }
        await websocket.send(json.dumps(say_action))
        response = await websocket.recv()
        print(f"服务器响应: {response}")
        
        # 第二阶段：发送眨眼动画
        eye_animation = {
            "type": "animation",
            "data": {
                "parameter": "EyeOpenLeft",
                "from": 1.0,
                "to": 0.0,
                "duration": 0.15,
                "delay": 0.0,
                "easing": "outSine"
            }
        }
        await websocket.send(json.dumps(eye_animation))
        response = await websocket.recv()
        print(f"服务器响应: {response}")
        
        # 第三阶段：发送嘴巴动画
        mouth_animation = {
            "type": "animation",
            "data": {
                "parameter": "MouthOpen",
                "to": 0.7,
                "duration": 0.5,
                "delay": 0.1,
                "easing": "inOutQuad"
            }
        }
        await websocket.send(json.dumps(mouth_animation))
        response = await websocket.recv()
        print(f"服务器响应: {response}")
        
        # 第四阶段：发送表情动作
        emotion_action = {
            "type": "emotion",
            "data": {

            },
        }
        await websocket.send(json.dumps(emotion_action))
        response = await websocket.recv()
        print(f"服务器响应: {response}")
        
        # 第五阶段：执行所有动作
        execute_command = {
            "type": "execute",
            "data": {
                "loop": 0
            }
        }
        await websocket.send(json.dumps(execute_command))
        response = await websocket.recv()
        print(f"服务器响应: {response}")
        
        # 第六阶段：发送一个包含多个动画的消息
        multiple_animations = {
            "type": "animation",
            "data": [
                {
                    "parameter": "EyeOpenRight",
                    "from": 1.0,
                    "to": 0.0,
                    "duration": 0.15,
                    "delay": 2.0,
                    "easing": "outSine"
                },
                {
                    "parameter": "MouthOpen",
                    "to": 0.5,
                    "duration": 0.3,
                    "delay": 2.1,
                    "easing": "inOutQuad"
                }
            ]
        }
        await websocket.send(json.dumps(multiple_animations))
        response = await websocket.recv()
        print(f"服务器响应: {response}")
        
        # 第七阶段：执行第二组动作
        await websocket.send(json.dumps(execute_command))
        response = await websocket.recv()
        print(f"服务器响应: {response}")

if __name__ == "__main__":
    asyncio.run(test_animation_control())