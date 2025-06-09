import asyncio
import json

import websockets


async def test_animation_control():
    uri = "ws://localhost:8080/ws/animate_control"
    
    async with websockets.connect(uri) as websocket:
        print("已连接到WebSocket服务器")
        expression = {
            "type": "play_preformed_animation",
            "data": {
                "name": "wink_proportional",
                "delay": 0,
            },
        }
        await websocket.send(json.dumps(expression))
        response = await websocket.recv()
        print(response)

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