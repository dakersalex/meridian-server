import subprocess
result = subprocess.run(
    ['grep', '-n', 'key_facts\|Call 3\|kf_prompt\|key fact\|max_tokens.*80\|max_tokens.*120\|max_tokens.*200\|max_tokens.*500\|max_tokens.*1000\|max_tokens.*1500\|max_tokens.*2000',
     '/Users/alexdakers/meridian-server/server.py'],
    capture_output=True, text=True
)
with open('/Users/alexdakers/meridian-server/tmp_themes_check.txt', 'w') as f:
    f.write(result.stdout)
print("DONE")
