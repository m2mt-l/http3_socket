import socket, time
from aioquic.buffer import Buffer
from aioquic.quic import packet
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.packet import QuicHeader
from aioquic.quic.connection import QuicConnection

from my_connection import MyConnection


class MyServer:
    # maximum UDP packet size
    PACKET_SIZE = 65536

    def __init__(self, ip: str, port: int, cert: str, key: str):
        self.ip = ip
        self.port = port
        # parameter for aioquic
        self.cfg = QuicConfiguration(
            alpn_protocols=["h3"],
            is_client=False,
            max_datagram_frame_size=self.PACKET_SIZE
        )
        self.cfg.load_cert_chain(cert, key)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.con_map = {}

    def start(self):
        server_addr = (self.ip, self.port)
        print(f"Opening port: {server_addr}")
        # open port
        self.server_socket.bind(server_addr)
        while True:
            # wait packets by recvfrom, if it receives packets call udp_packet_received
            data, client_adr = self.server_socket.recvfrom(MyServer.PACKET_SIZE)
            self.udp_packet_received(data, client_adr)

    def udp_packet_received(self, pkt: bytes, adr: tuple):
        # analyze packet header, return PcketHeader object
        hdr = packet.pull_quic_header(Buffer(data=pkt), self.cfg.connection_id_length)
        self.print_packet_header(pkt, hdr, "->")
        # check MyConnection object    
        mycon = self.con_map.get(hdr.destination_cid)
        # if no connection and packet is initial, make MyConnection object from QuicConnection object
        if mycon is None and hdr.packet_type == packet.PACKET_TYPE_INITIAL:
            con = QuicConnection(
                configuration=self.cfg,
                original_destination_connection_id=hdr.destination_cid
            )
            mycon = MyConnection(con)
            self.con_map[con.host_cid] = mycon
        
        if mycon is not None:
            # call udp_packet_received in MyObject and notify receiving UDP packets
            mycon.udp_packet_received(pkt, adr)
            self.send_packets(mycon.qcon)

    def print_packet_header(self, pkt: bytes, hdr: QuicHeader, prefix: str):
        print(f"{prefix} version={hdr.version}"
            + f" type={self.packet_type_name(hdr.packet_type)}"
            + f" scid={hdr.source_cid.hex()}"
            + f" dcid={hdr.destination_cid.hex()}"
            + f" token={hdr.token.hex()} len={len(pkt)}"
            )

    def packet_type_name(self, typ: int):
        if typ & packet.PACKET_LONG_HEADER == 0:
            return "Short"
        elif typ == packet.PACKET_TYPE_INITIAL:
            return "Initial"
        elif typ == packet.PACKET_TYPE_ZERO_RTT:
            return "0-RTT"
        elif typ == packet.PACKET_TYPE_HANDSHAKE:
            return "Handshake"
        elif typ == packet.PACKET_TYPE_RETRY:
            return "Retry"
        else:
            return "Unknown"

    def send_packets(self, con: QuicConnection):
        for pkt, adr in con.datagrams_to_send(now=time.time()):
            self.server_socket.sendto(pkt, adr)
            hdr = packet.pull_quic_header(
                Buffer(data=pkt),
                self.cfg.connection_id_length
            )
            self.print_packet_header(pkt, hdr, "<-")

    