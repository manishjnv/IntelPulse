import json, urllib.request
TOKEN = open('/tmp/token.txt').read().strip()

def get(path):
    req = urllib.request.Request('http://localhost:8000/api/v1' + path)
    req.add_header('Cookie', 'iw_session=' + TOKEN)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

# Dashboard
d = get('/enrichment/dashboard')
print('=== Dashboard keys:', list(d.keys()))
for key in ['active_campaigns', 'top_actors', 'sector_threats', 'trending_cves']:
    items = d.get(key, [])
    if items:
        print(key + ' [0] keys:', list(items[0].keys()))
        print(key + ' [0] sample:', json.dumps(items[0], default=str)[:300])
    print()

# Threat Velocity
print('=== Threat Velocity ===')
try:
    v = get('/enrichment/threat-velocity')
    print('type:', type(v).__name__)
    if isinstance(v, dict):
        print('keys:', list(v.keys()))
        items = v.get('items', v.get('cve', v.get('data', [])))
        if isinstance(items, list) and items:
            print('items[0]:', json.dumps(items[0], default=str)[:300])
    elif isinstance(v, list) and v:
        print('len:', len(v))
        print('[0]:', json.dumps(v[0], default=str)[:300])
except Exception as e:
    print('Error:', e)

# Technique usage
print()
print('=== Technique Usage ===')
try:
    t = get('/enrichment/technique-usage')
    print('type:', type(t).__name__)
    if isinstance(t, list):
        print('len:', len(t))
        if t:
            print('[0] keys:', list(t[0].keys()))
    elif isinstance(t, dict):
        print('keys:', list(t.keys()))
except Exception as e:
    print('Error:', e)

# Detection rules
print()
print('=== Detection Rules ===')
try:
    r = get('/enrichment/detection-rules?limit=2')
    print('type:', type(r).__name__)
    if isinstance(r, list):
        print('len:', len(r))
        if r:
            print('[0] keys:', list(r[0].keys()))
            print('[0] name:', r[0].get('name'), 'type:', r[0].get('rule_type'))
    elif isinstance(r, dict):
        print('keys:', list(r.keys()))
except Exception as e:
    print('Error:', e)

# Briefings
print()
print('=== Briefings ===')
try:
    b = get('/enrichment/briefings?limit=2')
    print('type:', type(b).__name__)
    if isinstance(b, list):
        print('len:', len(b))
        if b:
            print('[0] keys:', list(b[0].keys()))
    elif isinstance(b, dict):
        print('keys:', list(b.keys()))
except Exception as e:
    print('Error:', e)
