"""
清理Python缓存并提示重启
"""
import os
import shutil
from pathlib import Path

def clean_pycache(root_dir):
    """递归删除所有__pycache__目录"""
    count = 0
    for path in Path(root_dir).rglob('__pycache__'):
        if path.is_dir():
            try:
                shutil.rmtree(path)
                count += 1
                print(f"[OK] 删除: {path}")
            except Exception as e:
                print(f"[WARN] 无法删除 {path}: {e}")
    
    return count

def clean_pyc_files(root_dir):
    """递归删除所有.pyc文件"""
    count = 0
    for path in Path(root_dir).rglob('*.pyc'):
        try:
            path.unlink()
            count += 1
            print(f"[OK] 删除: {path}")
        except Exception as e:
            print(f"[WARN] 无法删除 {path}: {e}")
    
    return count

if __name__ == "__main__":
    print("=" * 60)
    print("清理Python缓存")
    print("=" * 60)
    
    vnpy_root = Path(__file__).parent.parent
    print(f"\n清理目录: {vnpy_root}")
    
    print("\n1. 清理 __pycache__ 目录...")
    pycache_count = clean_pycache(vnpy_root)
    print(f"   共删除 {pycache_count} 个 __pycache__ 目录")
    
    print("\n2. 清理 .pyc 文件...")
    pyc_count = clean_pyc_files(vnpy_root)
    print(f"   共删除 {pyc_count} 个 .pyc 文件")
    
    print("\n" + "=" * 60)
    print("清理完成！")
    print("=" * 60)
    print("\n请按以下步骤操作：")
    print("1. 关闭当前运行的vnpy程序")
    print("2. 重新启动vnpy程序")
    print("3. 执行回测并切换到Monitor Tab")
    print("4. 点击日线K线，观察分钟K线是否联动")
    print("\n如果还是不行，请检查:")
    print("- vnpy/strategy_condition/ui/kline_view.py 是否包含 bar_clicked 信号")
    print("- 确认程序启动时没有import错误")