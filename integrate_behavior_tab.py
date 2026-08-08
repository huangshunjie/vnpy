"""
BehaviorResearchTab integration script
"""
import os
import re

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
widget_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "ui", "widget.py")

print("=" * 80)
print("Integrating BehaviorResearchTab to main window")
print("=" * 80)

# Read file
with open(widget_file, 'r', encoding='utf-8') as f:
    content = f.read()

changes_made = False

# Step 1: Check import
if 'from .behavior_tab' in content:
    print("\n[OK] Import already exists")
else:
    print("\n[WARNING] Import not found")

# Step 2: Add tab instance
if 'self._behavior_tab' not in content:
    print("\n[Step 2] Adding tab instance...")
    
    pattern = r'(self\._feature_tab\s*=\s*FeatureTab\(self\.engine\))'
    replacement = r'\1\n        self._behavior_tab   = BehaviorResearchTab(self.engine)'
    
    content = re.sub(pattern, replacement, content)
    changes_made = True
    print("[OK] Tab instance added")
else:
    print("\n[OK] Tab instance already exists")

# Step 3: Add to tabs list
if '(self._behavior_tab,' not in content:
    print("\n[Step 3] Adding to tabs list...")
    
    pattern = r'(\(self\._feature_tab,\s*".*?Features.*?"\),)'
    replacement = r'\1\n            (self._behavior_tab,   "Behavior Research"),'
    
    content = re.sub(pattern, replacement, content)
    changes_made = True
    print("[OK] Added to tabs list")
else:
    print("\n[OK] Already in tabs list")

# Write back
if changes_made:
    with open(widget_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n" + "=" * 80)
    print("SUCCESS: Integration completed! File updated.")
else:
    print("\n" + "=" * 80)
    print("SUCCESS: All modifications already exist.")

print("=" * 80)
print("\nNext steps:")
print("1. Restart VN Trader")
print("2. Open Quant Research Platform")
print("3. Check for 'Behavior Research' tab")
print("\n" + "=" * 80)
