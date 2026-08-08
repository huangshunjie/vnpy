"""Fix indentation: method bodies need 8 spaces, not 4"""
path = "vnpy/quant_research/ui/behavior_tab.py"
lines = open(path, "r", encoding="utf-8").readlines()

# Find line 509 (0-indexed 508) where the appended methods start
# Everything from that line onward needs to be re-indented:
# - Lines starting with "    def " stay as-is (class method definitions at 4 spaces)
# - All other non-blank lines need +4 spaces (method body at 8 spaces)

# Find the start of the appended section
start_idx = None
for i, line in enumerate(lines):
    if "def _on_feature_double_click(self" in line and line.strip().startswith("def"):
        start_idx = i
        break

if start_idx is None:
    print("Could not find _on_feature_double_click")
    exit(1)

print(f"Found appended methods starting at line {start_idx + 1}")

# Re-indent lines from start_idx onward
output = lines[:start_idx]

for line in lines[start_idx:]:
    stripped = line.rstrip('\n')
    if stripped.strip() == "":
        output.append("\n")
    elif stripped.startswith("    def "):
        # Class method definition - correct at 4 spaces
        output.append(line)
    elif stripped.startswith("    "):
        # Method body at 4 spaces - needs to be 8 spaces
        output.append("    " + line)
    else:
        # Shouldn't happen, but keep as-is
        output.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(output)

print(f"Done! {len(output)} lines")

# Verify
import ast
try:
    code = open(path, "r", encoding="utf-8").read()
    ast.parse(code)
    print("Syntax OK!")
except SyntaxError as e:
    print(f"Still has syntax error: {e}")