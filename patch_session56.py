with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# Fix formatPubDate to also try added_at as fallback
old = "function formatPubDate(a){if(a.pub_date&&a.pub_date!=='null'&&a.pub_date!==''){const d=new Date(a.pub_date);if(!isNaN(d))return d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});return a.pub_date;}if(a.saved_at){const d=new Date(a.saved_at);if(!isNaN(d)&&d.getFullYear()>2000)return d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});}return '';}"
new = "function formatPubDate(a){if(a.pub_date&&a.pub_date!=='null'&&a.pub_date!==''){const d=new Date(a.pub_date);if(!isNaN(d))return d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});return a.pub_date;}const ts=a.saved_at||a.added_at;if(ts){const d=new Date(ts);if(!isNaN(d)&&d.getFullYear()>2000)return d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});}return '';}"

assert old in content, "formatPubDate not found"
content = content.replace(old, new, 1)

count = content.count('<html lang')
assert count == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done. html lang: {count}")
