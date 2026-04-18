#!/usr/bin/env python3
"""Fix relative API calls to use SERVER variable for proper local development"""

import re

# Read the file
with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# Count current issues
relative_calls = re.findall(r"fetch\s*\(\s*['\"]/?api/[^'\"]*['\"]", content)
print(f"Found {len(relative_calls)} relative API calls to fix")

# Fix patterns: fetch('/api/...') -> fetch(SERVER+'/api/...')
# Handle both quoted styles and optional leading slash
fixes = [
    (r"fetch\s*\(\s*['\"]/?api/([^'\"]*)['\"]", r"fetch(SERVER+'/api/\1'"),
    (r"fetch\s*\(\s*`/?api/([^`]*)`", r"fetch(SERVER+`/api/\1`")
]

for pattern, replacement in fixes:
    content = re.sub(pattern, replacement, content)

# Write back
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)

print("✅ Fixed all relative API calls to use SERVER variable")
print("🔄 Refresh the page to see improved performance")
