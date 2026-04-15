import ast

with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

old_model = 'claude-sonnet-4-20250514'
new_model = 'claude-sonnet-4-6'

count = content.count(old_model)
print(f"Found {count} instances of {old_model}")

content = content.replace(old_model, new_model)

assert old_model not in content, "Replacement incomplete"
print(f"Replaced all with {new_model}")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print("Done")
