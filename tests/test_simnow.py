import socket

servers = [
    ("180.168.146.187", 10202),
    ("180.168.146.187", 10902),
    ("180.168.146.197", 10212),
    ("180.168.146.197", 10912),
]
for host, port in servers:
    s = socket.socket()
    s.settimeout(5)
    r = s.connect_ex((host, port))
    status = "可达" if r == 0 else f"超时 code={r}"
    print(f"{host}:{port}  ->  {status}")
    s.close()
