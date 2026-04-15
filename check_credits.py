import json, urllib.request

key = json.load(open('/Users/alexdakers/meridian-server/credentials.json'))['anthropic_api_key']

# Try the usage/billing endpoint
req = urllib.request.Request(
    'https://api.anthropic.com/v1/usage',
    headers={
        'x-api-key': key,
        'anthropic-version': '2023-06-01'
    }
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(r.read().decode())
except Exception as e:
    print(f"Error: {e}")
