import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django_redis import get_redis_connection

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "chat_%s" % self.room_name

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get("message_type")
        pointer = text_data_json.get("pointer")

        if message_type == "draw":  # 그리는 중인 경우
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name, {
                    "type": "chat_message",
                    "message_type": "draw",
                    "pointer": pointer,
                }
            )
        elif message_type == "end":  # 그리기를 끝낸 경우
            redis_conn = get_redis_connection("default")
            id_ = redis_conn.incr("line_id")
            data = {"id": id_, "pointer": pointer}
            json_data = json.dumps(data)
            redis_conn.lpush("lines", json_data)

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name, {
                    "type": "chat_message",
                    "message_type": "end",
                    "data": data,
                }
            )

    # Receive message from room group
    def chat_message(self, event):
        message_type = event.get("message_type")
        if message_type == "draw":
            pointer = event.get("pointer")
            self.send(text_data=json.dumps({
                "message_type": "draw",
                "pointer": pointer,
            }))
        elif message_type == "end":
            data = event.get("data")
            self.send(text_data=json.dumps({
                "message_type": "end",
                "data": data,
            }))


# 을 그리더라도 여러번 저장되는 문제를 해결하기 위해 선이 그려질 때마다 Redis에 저장하는 것이 아니라, 마우스 클릭이 끝나는 시점에서 Redis에 저장하도록 구현할 수 있습니다.


import redis

# Redis에 연결합니다.
r = redis.Redis(host='localhost', port=6379, db=0)

# mylist에 요소를 추가합니다.
r.lpush('mylist', 'foo')
r.lpush('mylist', 'bar')
r.lpush('mylist', 'baz')

# 가장 마지막 요소를 가져옵니다.
last_element = r.rpop('mylist')
print(last_element)  # 출력 결과: b'foo'

# 다시 한번 가장 마지막 요소를 가져옵니다.
last_element = r.rpop('mylist')
print(last_element)  # 출력 결과: b'bar'

# 더 이상 가져올 요소가 없습니다.
last_element = r.rpop('mylist')
print(last_element)  # 출력 결과: None


==============================================================

코드에서 "end" 메시지를 받으면 Redis에 x, y 좌표값이 담긴 JSON 데이터를 lpush하도록 추가했기 때문에, 그 데이터를 가져와서 리스트를 만드는 것은 간단합니다.

아래와 같이 get_lines 함수를 추가하면 Redis에서 저장된 모든 선의 리스트를 가져올 수 있습니다.

def get_lines():
    redis_conn = get_redis_connection("default")
    lines = []
    for line in redis_conn.lrange("lines", 0, -1):
        data = json.loads(line)
        lines.append(data["pointer"])
    return lines

그리고 이 함수를 사용하여 connect 메소드에서 소켓 연결이 성공하면 현재 저장된 모든 선을 클라이언트에 전송할 수 있습니다.

def connect(self):
    self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
    self.room_group_name = "chat_%s" % self.room_name

    # Join room group
    async_to_sync(self.channel_layer.group_add)(
        self.room_group_name, self.channel_name
    )

    # Send initial lines to the client
    lines = get_lines()
    for pointer in lines:
        async_to_sync(self.channel_layer.send)(
            self.channel_name, {
                "type": "chat_message",
                "message_type": "draw",
                "pointer": pointer,
            }
        )

    self.accept()

위 코드에서 Redis에서 모든 선의 리스트를 가져와 lines 변수에 저장하고, 그 리스트에 담긴 모든 선을 클라이언트에 전송하는 부분을 추가했습니다.