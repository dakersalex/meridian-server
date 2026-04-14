import subprocess, sys
r = subprocess.run(
    ['curl', '-s', '-X', 'POST', 'http://localhost:4242/api/push-articles'],
    capture_output=True, text=True, timeout=300
)
print(r.stdout)
print(r.stderr, file=sys.stderr)
