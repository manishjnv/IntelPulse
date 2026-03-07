import json, urllib.request
TOKEN = open('/tmp/token.txt').read().strip()
req = urllib.request.Request('http://localhost:8000/api/v1/enrichment/dashboard')
req.add_header('Cookie', 'iw_session=' + TOKEN)
d = json.loads(urllib.request.urlopen(req, timeout=30).read())
for k, v in d.items():
    t = type(v).__name__
    if isinstance(v, dict):
        print(k, t, list(v.keys())[:5])
    elif isinstance(v, list):
        print(k, t, len(v), type(v[0]).__name__ if v else 'empty')
    else:
        print(k, t, str(v)[:80])
