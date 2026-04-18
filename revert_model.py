#!/usr/bin/env python3
"""Revert model references back to working alias"""

# Revert meridian.html
with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

old_model = 'claude-sonnet-4-6-20250217'
new_model = 'claude-sonnet-4-6'

updated_content = content.replace(old_model, new_model)
count = content.count(old_model)

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(updated_content)

print(f"Reverted {count} instances in meridian.html")

# Revert server.py
with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

updated_content = content.replace(old_model, new_model)
count = content.count(old_model)

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(updated_content)

print(f"Reverted {count} instances in server.py")
print("✅ Model references reverted to working alias claude-sonnet-4-6")
