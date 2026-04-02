import subprocess
result = subprocess.run(
    ['grep', '-n', 'kt_generate\|theme_prompt\|Call 1\|representative\|discriminat\|consolidat\|You are a\|def kt_seed', 
     '/Users/alexdakers/meridian-server/server.py'],
    capture_output=True, text=True
)
with open('/Users/alexdakers/meridian-server/tmp_grep_out.txt', 'w') as f:
    f.write(result.stdout + result.stderr)
print("DONE")
