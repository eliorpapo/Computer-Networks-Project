import socket
import struct
import random
import time
import platform
import pandas as pd

# OS detection
IS_MAC = (platform.system() == "Darwin")
IS_WINDOWS = (platform.system() == "Windows")


def checksum(data: bytes) -> int:
    """Compute Internet checksum (RFC 1071)."""
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def build_ip_header(src_ip: str, dst_ip: str, payload_len: int, proto: int = socket.IPPROTO_TCP) -> bytes:
    """
    Build IPv4 header.
    NOTE: On macOS/BSD with IP_HDRINCL, some stacks expect ip_len and ip_off in host byte order.
    """
    version_ihl = (4 << 4) + 5  # IPv4 + IHL=5 (20 bytes)
    tos = 0
    total_length = 20 + payload_len
    ident = random.randint(0, 65535)
    frag_off = 0
    ttl = 64

    src = socket.inet_aton(src_ip)
    dst = socket.inet_aton(dst_ip)

    if IS_MAC:
        # macOS/BSD: ip_len + ip_off often expected in host order with IP_HDRINCL
        header_start = struct.pack("!BB", version_ihl, tos)
        header_len_id_frag = struct.pack("HHH", total_length, ident, frag_off)  # host order
        header_rest = struct.pack("!BBH4s4s", ttl, proto, 0, src, dst)          # checksum=0 for now
        ip_header = header_start + header_len_id_frag + header_rest
    else:
        # Standard network order
        ip_header = struct.pack("!BBHHHBBH4s4s",
                                version_ihl, tos, total_length, ident, frag_off,
                                ttl, proto, 0, src, dst)

    ip_chk = checksum(ip_header)
    # Insert checksum (always network order)
    return ip_header[:10] + struct.pack("!H", ip_chk) + ip_header[12:]


def build_tcp_header(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                     payload: bytes = b"", flags: int = 0x18) -> bytes:
    """
    Build minimal TCP header + checksum using pseudo-header.
    flags default 0x18 = PSH + ACK (no real handshake; you may see RST from OS).
    """
    seq = random.randint(0, 0xFFFFFFFF)
    ack_seq = 0
    doff_res = (5 << 4)  # data offset = 5 (20 bytes), reserved=0
    window = socket.htons(5840)
    check = 0
    urg_ptr = 0

    tcp_header = struct.pack("!HHLLBBHHH",
                             src_port, dst_port,
                             seq, ack_seq,
                             doff_res, flags,
                             window, check, urg_ptr)

    # Pseudo header for checksum
    pseudo_hdr = struct.pack("!4s4sBBH",
                             socket.inet_aton(src_ip),
                             socket.inet_aton(dst_ip),
                             0,
                             socket.IPPROTO_TCP,
                             len(tcp_header) + len(payload))

    tcp_chk = checksum(pseudo_hdr + tcp_header + payload)

    # Final TCP header with checksum
    return struct.pack("!HHLLBBHHH",
                       src_port, dst_port,
                       seq, ack_seq,
                       doff_res, flags,
                       window, tcp_chk, urg_ptr)


class RawTcpTransport:
    def __init__(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = int(src_port)
        self.dst_port = int(dst_port)

        if IS_WINDOWS:
            raise RuntimeError("Windows usually blocks raw TCP crafting. Use Linux/macOS (sudo).")

        # IMPORTANT FIX:
        # Use IPPROTO_TCP (ip.proto=6) so Wireshark decodes it as TCP.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)

        # We provide the IP header ourselves
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    def send(self, data: bytes, flags: int = 0x18):
        tcp = build_tcp_header(self.src_ip, self.dst_ip, self.src_port, self.dst_port, data, flags=flags)
        ip = build_ip_header(self.src_ip, self.dst_ip, len(tcp) + len(data), proto=socket.IPPROTO_TCP)
        packet = ip + tcp + data

        # Port in sendto() is ignored for raw sockets; keep 0
        self.sock.sendto(packet, (self.dst_ip, 0))


def main():
    # Run settings (adjust if needed)
    SRC_IP = "127.0.0.1"
    DST_IP = "127.0.0.1"
    SRC_PORT = 54321
    DST_PORT = 12345

    transport = RawTcpTransport(SRC_IP, DST_IP, SRC_PORT, DST_PORT)

    # Read input CSV (expects column: message)
    df = pd.read_csv("group05_http_input.csv")

    for i, row in df.iterrows():
        msg = str(row["message"]) if "message" in row and not pd.isna(row["message"]) else f"Msg {i}"
        payload = msg.encode("utf-8", errors="replace")

        print(f"Sending #{i}: src={SRC_IP}:{SRC_PORT} -> dst={DST_IP}:{DST_PORT} | {msg[:40]!r}")
        transport.send(payload, flags=0x18)  # PSH+ACK
        time.sleep(0.2)

    print("Done!")


if __name__ == "__main__":
    try:
        main()
    except PermissionError:
        print("PermissionError: run with sudo (macOS/Linux): sudo python3 raw_tcp_sender.py")
    except Exception as e:
        print(f"Error: {e}")

        # ip.addr == 127.0.0.1 && tcp.port == 12345
        # python3 -m venv venv
        # source venv/bin/activate
        # pip install pandas
        # sudo python3 file.py

