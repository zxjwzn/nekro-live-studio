import asyncio
import websockets
import json

async def test_animation_control():
    uri = "ws://localhost:8080/ws/animate_control"
    
    async with websockets.connect(uri) as websocket:
        print("已连接到WebSocket服务器")
        
        # 第二阶段：发送眨眼动画
        eye_animation = {
            "type": "animation",
            "data": {
                "parameter": "FaceAngleZ",
                "from": 30.0,
                "to": -30.0,
                "duration": 2,
                "delay": 0.0,
                "easing": "outSine"
            }
        }
        await websocket.send(json.dumps(eye_animation))
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

if __name__ == "__main__":
    asyncio.run(test_animation_control())