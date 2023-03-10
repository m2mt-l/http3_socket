import socket, time, os
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
            max_datagram_frame_size=self.PACKET_SIZE,
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

        if hdr.version and hdr.version not in self.cfg.supported_versions:
            self.negotiate_version(hdr, adr)
            return

        # check MyConnection object
        mycon = self.con_map.get(hdr.destination_cid)
        # if no connection and packet is initial, make MyConnection object from QuicConnection object
        if mycon is None and hdr.packet_type == packet.PACKET_TYPE_INITIAL:

            # if initial packets do not have a token, call retry
            if not hdr.token:
                self.retry(hdr, adr)
                return
            # retrieve a new connection id and old id(dcid)
            retry_scid = hdr.token[0:8]
            original_dcid = hdr.token[8:]
            con = QuicConnection(
                configuration=self.cfg,
                retry_source_connection_id=retry_scid,
                original_destination_connection_id=original_dcid,
            )
            mycon = MyConnection(con)
            self.con_map[con.host_cid] = mycon

        if mycon is not None:
            # call udp_packet_received in MyObject and notify receiving UDP packets
            mycon.udp_packet_received(pkt, adr)
            self.send_packets(mycon.qcon)

    def print_packet_header(self, pkt: bytes, hdr: QuicHeader, prefix: str):
        print(
            f"{prefix} version={hdr.version}"
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
                Buffer(data=pkt), self.cfg.connection_id_length
            )
            self.print_packet_header(pkt, hdr, "<-")

    def negotiate_version(self, hdr: QuicHeader, adr: tuple):
        # encode_quic_version_negotiation: generate QUIC packets for version negotiation
        pkt = packet.encode_quic_version_negotiation(
            source_cid=hdr.destination_cid,
            destination_cid=hdr.source_cid,
            supported_versions=self.cfg.supported_versions,
        )
        self.server_socket.sendto(pkt, adr)

        hdr = packet.pull_quic_header(Buffer(data=pkt), self.cfg.connection_id_length)
        self.print_packet_header(pkt, hdr, "<-")

    def retry(self, hdr: QuicHeader, adr: tuple):
        # generate a 8-byte random new id
        new_cid = os.urandom(8)
        token = new_cid + hdr.destination_cid

        pkt = packet.encode_quic_retry(
            version=hdr.version,
            source_cid=new_cid,
            destination_cid=hdr.source_cid,
            original_destination_cid=hdr.destination_cid,
            retry_token=token,
        )
        self.server_socket.sendto(pkt, adr)

        hdr = packet.pull_quic_header(Buffer(data=pkt), self.cfg.connection_id_length)
        self.print_packet_header(pkt, hdr, "<-")
