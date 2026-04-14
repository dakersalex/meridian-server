with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    lines = f.readlines()

# Find exact start/end of FA scraper class
start_line = None
end_line = None
for i, line in enumerate(lines):
    if '"""Scrapes Foreign Affairs from two sources:' in line:
        # Walk back to find the class/def start
        for j in range(i, max(0, i-10), -1):
            if lines[j].strip().startswith('class ') or (lines[j].strip().startswith('def ') and 'fa' in lines[j].lower()):
                start_line = j
                break
        if start_line is None:
            start_line = i - 2
    if start_line is not None and end_line is None:
        # Find end: next top-level def or class after start
        for j in range(start_line + 5, len(lines)):
            if lines[j].startswith('def ') or lines[j].startswith('class '):
                end_line = j
                break

print(f"FA scraper: lines {start_line+1} to {end_line}")
print("Start:", lines[start_line].rstrip())
print("End boundary:", lines[end_line].rstrip())
