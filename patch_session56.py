import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Find the routing block where scores are compared against thresholds
# Need to add per-source logic: FA >= 7, others >= 8
old_threshold = (
    '        if _score >= 8:\n'
    '            if _already_manual:\n'
    '                # Already saved manually — don\'t duplicate, just log\n'
    '                log.info(f"AI pick: score={_score} — already manually saved, skipping duplicate")\n'
    '                continue\n'
    '            feed_articles.append({'
)
new_threshold = (
    '        _feed_threshold = 7 if _source == "Foreign Affairs" else 8\n'
    '        if _score >= _feed_threshold:\n'
    '            if _already_manual:\n'
    '                # Already saved manually — don\'t duplicate, just log\n'
    '                log.info(f"AI pick: score={_score} — already manually saved, skipping duplicate")\n'
    '                continue\n'
    '            feed_articles.append({'
)
assert old_threshold in content, "Threshold pattern not found"
content = content.replace(old_threshold, new_threshold, 1)
print("Feed threshold patch applied")

# Also fix the suggested threshold check
old_suggested = '        elif _score >= 6:\n'
new_suggested = '        elif _score >= 6 and _score < _feed_threshold:\n'
assert old_suggested in content, "Suggested threshold not found"
content = content.replace(old_suggested, new_suggested, 1)
print("Suggested threshold patch applied")

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
