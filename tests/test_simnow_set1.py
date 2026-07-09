import socket

servers = [
    ("182.254.243.31", 30001),
    ("182.254.243.31", 30011),
    ("182.254.243.31", 30002),
    ("182.254.243.31", 30012),
    ("182.254.243.31", 30003),
    ("182.254.243.31", 30013),
]
for host, port in servers:
    s = socket.socket()
    s.settimeout(6)
    r = s.connect_ex((host, port))
    status = "可达" if r == 0 else f"code={r}"
    print(f"{host}:{port}  ->  {status}")
    s.close()
