import ast

with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# The suggested card div — add padding-bottom to match feed cards
old = "'<div class=\"' + (isFirst ? 'featured-card' : 'article-card') + '\" style=\"position:relative;padding-top:14px;opacity:' + cardOpacity + '\" id=\"sug-card-' + a.id + '\">'"
new = "'<div class=\"' + (isFirst ? 'featured-card' : 'article-card') + '\" style=\"position:relative;padding-top:14px;padding-bottom:14px;opacity:' + cardOpacity + '\" id=\"sug-card-' + a.id + '\">'"

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)
print("Padding fix applied")

# Verify HTML is still valid (check for single html tag)
import subprocess
count = content.count('<html lang')
print(f"html lang count: {count}")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print("Done")
