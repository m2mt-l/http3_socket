import time
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import HandshakeCompleted, StreamDataReceived
from aioquic.h3.connection import H3Connection

from my_stream import MyStream


class MyConnection:
    def __init__(self, con: QuicConnection):
        self.qcon = con
        self.h3con = None
        self.stream_map = {}

    def udp_packet_received(self, pkt: bytes, adr: tuple):
        self.qcon.receive_datagram(pkt, adr, time.time())
        self.handle_quic_events(self.qcon)

    def handle_quic_events(self, con: QuicConnection):
        while True:
            ev = con.next_event()
            if ev is None:
                break
            print(f"QUIC Event: {ev}")

            if isinstance(ev, HandshakeCompleted):
                self.h3con = H3Connection(con)
            elif isinstance(ev, StreamDataReceived):
                self.stream_data_received(ev)

    def stream_data_received(self, ev: StreamDataReceived):
        stream = self.stream_map.get(ev.stream_id)
        if stream is None:
            stream = MyStream(self, ev.stream_id)
            self.stream_map[ev.stream_id] = stream
        # H3Connection handle_event
        # Analyze QUIC events and return arrays of http3 events
        for hev in self.h3con.handle_event(ev):
            stream.h3_event_received(hev)
