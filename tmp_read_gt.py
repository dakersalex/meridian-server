s = open('/Users/alexdakers/meridian-server/meridian.html').read()
idx = s.find('async function generateThemes')
if idx < 0:
    idx = s.find('function generateThemes')
print('Found at:', idx)
print(repr(s[idx:idx+1200]))
