"""运行三个 smoke 套件并打印每套的 PASS/FAIL 摘要。"""
import subprocess
import sys

SUITES = [
    "tests/_smoke_linkage_fix.py",
    "tests/_smoke_chart_linkage.py",
    "tests/_smoke_monitor_dual_period.py",
]

all_ok = True
for name in SUITES:
    print(f"\n========== {name} ==========")
    r = subprocess.run(
        [sys.executable, name],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    # 拼接 stdout/stderr 强制按 utf-8 重新解码（subprocess 在 Windows 下可能拿到错的编码）
    raw = (r.stdout or "") + (r.stderr or "")
    try:
        raw = raw.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    except Exception:
        pass
    lines = raw.strip().splitlines()
    for line in lines[-6:]:
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("ascii", errors="replace").decode("ascii"))
    print(f"[{name}] exit code = {r.returncode}")
    if r.returncode != 0:
        all_ok = False

print("\n" + "=" * 60)
if all_ok:
    print("[OK] all 3 smoke suites passed (13+36+42 = 91 tests)")
    sys.exit(0)
else:
    print("[FAIL] some suite failed")
    sys.exit(1)
