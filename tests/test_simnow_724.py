import socket

for port in [40001, 40011]:
    s = socket.socket()
    s.settimeout(8)
    r = s.connect_ex(("182.254.243.31", port))
    print(f"182.254.243.31:{port}  ->  {'可达' if r == 0 else f'code={r}'}")
    s.close()
