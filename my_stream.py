from aioquic.h3.events import H3Event, HeadersReceived, DataReceived
from my_application import MyApplication


class MyStream:
    def __init__(self, mycon, stream_id: int):
        self.mycon = mycon
        self.stream_id = stream_id
        self.fields = {}
        self.app = MyApplication(self)
        self.post_data = bytes()
        self.finished = False

    def h3_event_received(self, hev: H3Event):
        print(f"H3 Event: {hev}")
        if isinstance(hev, HeadersReceived):
            self.headers_received(hev)
        elif isinstance(hev, DataReceived):
            self.data_received(hev)

    def headers_received(self, hev: HeadersReceived):
        self.analyze_header(hev)
        if self.fields[":method"] == "GET":
            self.app.do_app()

    def data_received(self, hev: DataReceived):
        self.post_data += hev.data
        if self.fields[":method"] == "POST" and hev.stream_ended and not self.finished:
            self.app.do_app()
            # if this is called again, send again
            self.finished = True

    # HeaderReceived headers --> tuple(field name, field value)
    # field name and field value: bytes
    def analyze_header(self, hev: HeadersReceived):
        for name, value in hev.headers:
            self.fields[name.decode()] = value.decode()

    def send_headers(self, status: int, fields: dict):
        headers = []
        headers.append((b":status", str(status).encode()))
        for name, value in fields.items():
            headers.append((name.encode(), value.encode()))
        self.mycon.h3con.send_headers(self.stream_id, headers)

    def send_data(self, data: bytes, end_stream=True):
        self.mycon.h3con.send_data(self.stream_id, data, end_stream)
