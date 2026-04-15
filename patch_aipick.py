import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Fix 1: Gate — widen midday window from hour >= 12 to hour >= 13
# This gives the 11:40 trigger a full hour of buffer before it's considered "midday"
old_gate = "    _gate_key = 'ai_pick_last_run_morning' if _now_h < 12 else 'ai_pick_last_run_midday'"
new_gate = "    _gate_key = 'ai_pick_last_run_morning' if _now_h < 13 else 'ai_pick_last_run_midday'"
assert old_gate in content, "Gate pattern not found"
content = content.replace(old_gate, new_gate, 1)
print("Fix 1 (gate): applied")

# Fix 2: Threshold — lower from >= 9 to >= 8 in both FT/FA and Economist scoring
old_thresh = "        if _score >= 9:"
new_thresh = "        if _score >= 8:"
count = content.count(old_thresh)
assert count == 2, f"Expected 2 threshold instances, found {count}"
content = content.replace(old_thresh, new_thresh)
print(f"Fix 2 (threshold): applied to {count} locations")

# Verify syntax
ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
