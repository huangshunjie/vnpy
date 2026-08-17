import sys  
sys.path.insert(0, '.')  
  
with open('vnpy/strategy_condition/ui/widget.py', 'r', encoding='utf-8') as f:  
    content = f.read()  
  
# Fix _on_pool_changed to always show update time  
old_text = 'self._pool_count_lbl.setText(f"{name} - {n} \u53ea{time_str}")'  
if old_text in content:  
    print('Found existing time_str usage in _on_pool_changed')  
else:  
    print('time_str not found - checking alternative patterns')  
  
# Check for the simpler pattern without time_str  
simple = 'self._pool_count_lbl.setText(f"{name} - {n} \u53ea")'  
if simple in content:  
    print('Found simple pattern without time_str') 
