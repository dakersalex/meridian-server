import subprocess

# Read current nginx config
result = subprocess.run(
    ["ssh", "root@204.168.179.158", "cat /etc/nginx/sites-available/meridian"],
    capture_output=True, text=True
)
print("CURRENT CONFIG:")
print(result.stdout)
print("STDERR:", result.stderr)
