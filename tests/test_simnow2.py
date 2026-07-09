import socket

# 先测试能否正常访问公网
test_servers = [
    ("8.8.8.8", 53),          # Google DNS
    ("180.168.146.187", 10202), # SimNow 交易
    ("180.168.146.187", 10902), # SimNow 交易备用
]
for host, port in test_servers:
    s = socket.socket()
    s.settimeout(5)
    r = s.connect_ex((host, port))
    status = "可达" if r == 0 else f"超时"
    print(f"{host}:{port}  ->  {status}")
    s.close()
