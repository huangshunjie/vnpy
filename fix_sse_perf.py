# -*- coding: utf-8 -*-  
from pathlib import Path  
  
file_path = Path("vnpy/trader/stock_pool.py")  
content = file_path.read_text("utf-8")  
  
# Step 1  
if "_SYMBOLS_BY_EXCHANGE_CACHE" not in content:  
    loc = content.find("_LOCAL_SYMBOLS_CACHE")  
    line_end = content.find(chr(10), loc)  
    content = content[:line_end+1] + "_SYMBOLS_BY_EXCHANGE_CACHE: Dict[str, List[str]] = {}" + chr(10) + content[line_end+1:]  
    print("Added cache variable")  
  
file_path.write_text(content, "utf-8")  
print("Done!")  
