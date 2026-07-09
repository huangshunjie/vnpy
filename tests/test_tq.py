import socket

servers = [
    ("openmd.shinnytech.com", 443),
    ("openmd.shinnytech.com", 80),
]
for host, port in servers:
    try:
        s = socket.socket()
        s.settimeout(5)
        r = s.connect_ex((host, port))
        print(f"{host}:{port}  ->  {'可达' if r == 0 else f'超时 code={r}'}")
        s.close()
    except Exception as e:
        print(f"{host}:{port}  ->  失败: {e}")
