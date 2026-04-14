with open('/Users/alexdakers/meridian-server/wake_and_sync.sh', 'r') as f:
    content = f.read()

# Find the start and end markers of the old push block
start_marker = "# Push all full_text articles from Mac DB to VPS"
end_marker = "PYEOF"

start_idx = content.find(start_marker)
assert start_idx != -1, "Start marker not found"

# Find the PYEOF that ends the push block (first one after start)
end_idx = content.find(end_marker, start_idx)
assert end_idx != -1, "End marker not found"
end_idx += len(end_marker)  # include PYEOF itself

old_block = content[start_idx:end_idx]

new_block = """# Push new/updated articles from Mac DB to VPS (incremental).
# vps_push.py: only sends articles newer than last_push_ts watermark (last 48h minimum).
# Also pushes kt_meta last_sync timestamps to VPS unconditionally.
echo "$(date): Pushing articles to VPS" >> "$LOG"
python3 /Users/alexdakers/meridian-server/vps_push.py >> "$LOG" 2>&1"""

content = content.replace(old_block, new_block, 1)

with open('/Users/alexdakers/meridian-server/wake_and_sync.sh', 'w') as f:
    f.write(content)

print("Done. Old block length:", len(old_block))
print("New block length:", len(new_block))

# Verify it looks right
idx = content.find("vps_push.py")
print("Context around new block:")
print(content[idx-100:idx+200])
