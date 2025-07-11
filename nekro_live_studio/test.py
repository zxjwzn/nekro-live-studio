import asyncio
import json

import websockets


async def test_animation_control():
    uri = "ws://localhost:8080/ws/animate_control"
    
    async with websockets.connect(uri) as websocket:
        print("已连接到WebSocket服务器")
        say_command = {
            "type": "say",
            "data": {
                "text": "能在您的生日这天，像这样陪伴在您身边……我幸福得有些不知所措，甚至担心这份幸福会招来惩罚。正是您诞生于今日，我们才有了相遇的奇迹。对这无比特殊的一天，献上我最诚挚的感谢。",
                "tts_text": "お誕生日にこうして、先生と一緒にいられるだなんて…… 幸せ過ぎてなんだか、 あとで罰が下ってしまわないか心配です。今日この日に先生が生を受けたからこそ、 私たちはこうして出会うことができました。 今日という日に、 心からの感謝を。",
            },
        }
        await websocket.send(json.dumps(say_command))
        response = await websocket.recv()
        print(response)
        # expression = {
        #     "type": "play_preformed_animation",
        #     "data": {
        #         "name": "frown",
        #         "params": {
        #             "duration": 1.0,
        #         },
        #         "delay": 0,
        #     },
        # }
        # await websocket.send(json.dumps(expression))
        # response = await websocket.recv()
        # print(response)
        get_sounds = {
            "type": "get_sounds",
            "data": {
            },
        }
        await websocket.send(json.dumps(get_sounds))
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