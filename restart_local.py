import subprocess, time
subprocess.run('lsof -ti tcp:4242 | xargs kill -9', shell=True)
time.sleep(3)
# launchd will respawn automatically
print("killed")
