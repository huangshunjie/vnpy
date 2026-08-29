"""
V10 工具脚本：清空 strategy_condition 相关的 .pyc 缓存，
并打印 version banner 确认下一次启动是最新代码。

用法（在 vnpy 项目根目录）：
    python tests/_v10_clean_pycache_and_verify.py

之后正常启动 vnpy（python xxx.py run）即可。
启动后第一行 banner 应该看到：
    [Monitor-Banner] version=Monitor日线↔分钟联动 V10 (2026-08-23_21-43)
                       file=...\vnpy\strategy_condition\ui\condition_monitor_widget.py
                       mtime=2026-08-23 21:43:xx

如果不是 V10 而是 V8/V9 等更早版本，说明 .pyc 还没清干净，
请重新运行本脚本，或手动删除：
    find . -name "__pycache__" -path "*strategy_condition*" -exec rm -rf {} +
"""
import os
import shutil
import sys
import time


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))


def _walk_pycaches(root: str):
    """生成 (dir, file) 元组列表，包含所有 strategy_condition 相关的 .pyc"""
    for dirpath, dirnames, filenames in os.walk(root):
        if "__pycache__" not in dirpath:
            continue
        if "strategy_condition" not in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".pyc"):
                yield os.path.join(dirpath, fn)


def main():
    target = os.path.join(PROJECT_ROOT, "vnpy", "strategy_condition")
    print(f"[V10-clean] project root: {PROJECT_ROOT}")
    print(f"[V10-clean] target: {target}")

    removed = 0
    for pyc in _walk_pycaches(target):
        try:
            os.remove(pyc)
            print(f"[V10-clean] removed: {pyc}")
            removed += 1
        except Exception as e:
            print(f"[V10-clean] failed: {pyc}: {e}")

    # 删除整个 __pycache__ 目录（更彻底）
    for dirpath, dirnames, _ in os.walk(target):
        if "__pycache__" in dirnames:
            cache_dir = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(cache_dir)
                print(f"[V10-clean] rmtree: {cache_dir}")
                removed += 1
            except Exception as e:
                print(f"[V10-clean] rmtree failed: {cache_dir}: {e}")

    print(f"[V10-clean] done, removed {removed} caches")

    # ── 直接 import 该模块，触发 print 一次 banner ──
    print("\n[V10-clean] verifying by import:")
    try:
        import vnpy.strategy_condition.ui.condition_monitor_widget as m
        print(f"[V10-clean] module loaded: {m.__file__}")
    except Exception as e:
        print(f"[V10-clean] import failed: {e}")


if __name__ == "__main__":
    main()