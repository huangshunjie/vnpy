import re  
  
# 读取文件  
with open('vnpy/strategy_condition/ui/widget.py', 'r', encoding='utf-8') as f:  
    content = f.read()  
  
# 备份  
with open('vnpy/strategy_condition/ui/widget.py.bak', 'w', encoding='utf-8') as f:  
    f.write(content)  
  
# 替换  
content = content.replace('self._pool_count_lbl.setText(f\"{name} - {n} 只\")', 'self._pool_count_lbl.setText(f\"{name} - {n} 只{time_str}\")')  
  
# 在函数中添加时间获取代码  
pattern = r'(def _on_pool_changed.*?name = getattr.*)'  
replacement = r'\1\n\n        # 获取更新时间\n        try:\n            from vnpy.trader import stock_pool\n            update_time = stock_pool.get_pool_update_time()\n            time_str = f\" (更新: {update_time})\" if update_time else \"\"\n        except:\n            time_str = \"\"'  
content = re.sub(pattern, replacement, content, flags=re.DOTALL)  
  
# 写回  
with open('vnpy/strategy_condition/ui/widget.py', 'w', encoding='utf-8') as f:  
    f.write(content)  
  
print('修复完成!') 
