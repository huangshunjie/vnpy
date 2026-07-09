"""find_strategy_dir.py"""
import sys, pathlib
sys.path.insert(0, r"c:\Users\11229\Documents\GitHub\vnpy")

from vnpy.trader.utility import get_folder_path

strat_dir = get_folder_path("cta_strategy") / "strategies"
print("strategy dir:", strat_dir)
print("exists:", strat_dir.exists())
if strat_dir.exists():
    for f in sorted(strat_dir.iterdir()):
        print(" ", f.name)
