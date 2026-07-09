import socket

servers = [
    ("www.okx.com", 443),
    ("aws.okx.com", 443),
]
for host, port in servers:
    s = socket.socket()
    s.settimeout(5)
    r = s.connect_ex((host, port))
    print(f"{host}:{port}  ->  {'可达' if r == 0 else f'超时 code={r}'}")
    s.close()
