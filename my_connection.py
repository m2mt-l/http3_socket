import time
from aioquic.quic.connection import QuicConnection

class MyConnection:
    def __init__(self, con: QuicConnection):
        self.qcon = con

    def udp_packet_received(self, pkt: bytes, adr: tuple):
        self.qcon.receive_datagram(pkt, adr, time.time())
        self.handle_quic_events(self.qcon)

    def handle_quic_events(self, con: QuicConnection):
        while True:
            ev = con.next_event()
            if ev is None:
                break
            print(f"QUIC Event: {ev}")
            