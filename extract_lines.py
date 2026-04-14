with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    lines = f.readlines()

# Find the push_articles function and the push_images function start
# to understand exact line ranges
for i, line in enumerate(lines, 1):
    if '@app.route("/api/push-articles"' in line or '@app.route("/api/push-images"' in line or '@app.route("/api/push-newsletters"' in line:
        print(f"{i}: {line.rstrip()}")
