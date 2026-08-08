"""Fix behavior_tab.py - remove duplicate and fix indentation"""
path = "vnpy/quant_research/ui/behavior_tab.py"
lines = open(path, "r", encoding="utf-8").readlines()

# Find where the problem starts: the nested "def _on_feature_double_click" at wrong indent
# It should be at class method level (4 spaces), but it's at 8 spaces (nested)
# Find first occurrence of _set_logic method, keep it, then remove everything after
# that has wrong indentation

# Strategy: find `def _set_logic` and keep up to its proper body,
# then find the spurious nested `def _on_feature_double_click` and remove it
# Then find the proper `def _on_feature_double_click` at 4-space indent

# Let's find line 508 area
# Line 507 (0-indexed): blank
# Line 508: "        def _on_feature_double_click(self, item, col):\n" <- WRONG (8 spaces = nested)
# This should not be nested. The issue is that the appended block used 8-space indent for method defs.

# Fix approach: everything from `_set_logic` method's last line onwards, 
# replace the 8-space method definitions with 4-space ones

# Find the _set_logic method start
set_logic_start = None
for i, line in enumerate(lines):
    if "def _set_logic(self" in line and line.startswith("    def"):
        set_logic_start = i
        break

if set_logic_start is None:
    print("Could not find _set_logic")
    exit(1)

# Find where _set_logic body ends (next method at 4-space indent)
# The _set_logic method body uses 8-space indent
# After _set_logic, we want the appended methods to be at 4-space indent

# Actually the real issue: the raw string in _fix_behavior_tab.py used 8 spaces
# for method bodies (since inside the triple-quoted string, 4 spaces for def + 4 for body)
# But when we search for "def _on_feature_double_click" in the content to strip,
# there was still a partial def left from the original truncated file.

# Simplest fix: find all lines from the first occurrence of 
# "        def _on_feature_double_click" (8 spaces) and dedent them by 4

# Actually even simpler: rebuild from scratch. 
# Keep everything up to _set_logic body end, then append properly indented methods.

# Find end of _set_logic
# _set_logic body: lines after set_logic_start until we hit a line that starts with
# "    def " or "        def " that's a new method

# Let's just find the problematic section and fix indentation
output = []
i = 0
while i < len(lines):
    line = lines[i]
    # If we find a nested def at 8 spaces that should be at 4 spaces (class method level)
    if line.startswith("        def _on_feature_double_click(self"):
        # This and everything after should be dedented by 4
        for j in range(i, len(lines)):
            l = lines[j]
            if l.startswith("        "):
                output.append(l[4:])  # remove 4 spaces
            elif l.strip() == "":
                output.append(l)
            else:
                output.append(l)
        break
    else:
        output.append(line)
        i += 1

# Also need to fix: _set_logic had its last line as "self._refresh_cond_tree()" 
# which was part of the method body. After that the new methods should start.
# But the _set_logic method itself is incomplete - it was:
#   def _set_logic(self, is_and):
#       self._logic_op = "AND" if is_and else "OR"
#       self._logic_and_btn.setChecked(is_and)
#       self._logic_or_btn.setChecked(not is_and)
#       self._refresh_cond_tree()
# Then blank line, then next method.
# After dedent, the blank line + next method should be fine.

with open(path, "w", encoding="utf-8") as f:
    f.writelines(output)

print(f"Fixed! {len(output)} lines written")