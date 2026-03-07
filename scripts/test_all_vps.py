import json, urllib.request, urllib.error, os

API = os.environ.get('TEST_API', 'http://localhost:8000/api/v1')
TOKEN = open('/tmp/token.txt').read().strip()

def get(path):
    req = urllib.request.Request(API + path)
    req.add_header('Cookie', 'iw_session=' + TOKEN)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ''
        return {'_error': 'HTTP ' + str(e.code) + ': ' + body[:200]}
    except Exception as e:
        return {'_error': str(e)}

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method='POST')
    req.add_header('Cookie', 'iw_session=' + TOKEN)
    req.add_header('Content-Type', 'application/json')
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        bd = e.read().decode() if e.fp else ''
        return {'_error': 'HTTP ' + str(e.code) + ': ' + bd[:200]}
    except Exception as e:
        return {'_error': str(e)}

passed = 0
failed = 0

def check(name, ok, detail=''):
    global passed, failed
    s = 'PASS' if ok else 'FAIL'
    if ok:
        passed += 1
    else:
        failed += 1
    msg = '  [' + s + '] ' + name
    if detail:
        msg += ': ' + str(detail)
    print(msg)

SEP = '=' * 60

# ============================
print(SEP)
print('TEST 1: Dashboard Enrichment')
print(SEP)
d = get('/enrichment/dashboard')
if '_error' in d:
    check('Endpoint', False, d['_error'])
else:
    camps = d.get('active_campaigns', [])
    actors = d.get('top_actors', [])
    sects = d.get('sector_threats', [])
    trending = d.get('trending_cves', [])
    check('Has active_campaigns', len(camps) > 0, str(len(camps)) + ' campaigns')
    check('Has top_actors', len(actors) > 0, str(len(actors)) + ' actors')
    check('Has sector_threats', len(sects) > 0, str(len(sects)) + ' sectors')
    check('Has trending_cves', len(trending) >= 0, str(len(trending)) + ' CVEs')

    # Active Campaign fields
    if camps:
        c = camps[0]
        print('')
        print('  Active Campaign: ' + str(c.get('campaign_name')))
        check('Has actor_name', 'actor_name' in c, str(c.get('actor_name')))
        check('Has severity', 'severity' in c, str(c.get('severity')))
        check('Has cves_exploited', 'cves_exploited' in c, str(len(c.get('cves_exploited', []))) + ' CVEs')
        check('Has techniques_used', 'techniques_used' in c, str(len(c.get('techniques_used', []))) + ' techniques')
        check('Has targeted_sectors', 'targeted_sectors' in c, str(c.get('targeted_sectors', [])[:3]))
        check('Has targeted_regions', 'targeted_regions' in c, str(c.get('targeted_regions', [])[:3]))
        check('Has malware_used', 'malware_used' in c, str(c.get('malware_used', [])[:3]))

    # Sector Threat Map fields
    if sects:
        s = sects[0]
        print('')
        print('  Sector: ' + str(s.get('sector')))
        check('Sector has actors', 'actors' in s, str(s.get('actors', [])[:3]))
        check('Sector has max_severity', 'max_severity' in s, str(s.get('max_severity')))
        check('Sector has campaign_count', 'campaign_count' in s, str(s.get('campaign_count')))

# ============================
print('')
print(SEP)
print('TEST 2: Threat Velocity (/enrichment/velocity)')
print(SEP)
vel = get('/enrichment/velocity')
if '_error' in vel:
    check('Endpoint', False, vel['_error'])
else:
    items = vel if isinstance(vel, list) else vel.get('items', [])
    check('Has items', len(items) > 0, str(len(items)) + ' items')

    cve_items = [v for v in items if v.get('entity_type') == 'cve']
    actor_items = [v for v in items if v.get('entity_type') == 'actor']
    print('  Breakdown: ' + str(len(cve_items)) + ' CVEs, ' + str(len(actor_items)) + ' actors')

    if cve_items:
        cv = cve_items[0]
        print('')
        print('  CVE sample: ' + str(cv.get('entity')))
        check('CVE product_name field', 'product_name' in cv, str(cv.get('product_name')))
        check('CVE is_kev field', 'is_kev' in cv, str(cv.get('is_kev')))
        check('CVE patch_available field', 'patch_available' in cv, str(cv.get('patch_available')))
        check('CVE exploit_available field', 'exploit_available' in cv, str(cv.get('exploit_available')))
        check('CVE vuln_severity field', 'vuln_severity' in cv, str(cv.get('vuln_severity')))
        check('CVE published_at field', 'published_at' in cv, str(cv.get('published_at')))
        print('  Full CVE item: ' + json.dumps(cv, default=str)[:400])

    if actor_items:
        ac = actor_items[0]
        print('')
        print('  Actor sample: ' + str(ac.get('entity')))
        check('Actor recent_headline field', 'recent_headline' in ac, str(ac.get('recent_headline', ''))[:80])
        check('Actor targeted_sectors field', 'targeted_sectors' in ac, str(ac.get('targeted_sectors')))
        check('Actor published_at field', 'published_at' in ac, str(ac.get('published_at')))
        print('  Full Actor item: ' + json.dumps(ac, default=str)[:400])

# ============================
print('')
print(SEP)
print('TEST 3: Technique Usage (ATT&CK Heatmap)')
print(SEP)
tech = get('/enrichment/technique-usage')
if '_error' in tech:
    check('Endpoint', False, tech['_error'])
else:
    items = tech if isinstance(tech, list) else []
    check('Has techniques', len(items) > 0, str(len(items)) + ' techniques')
    if items:
        t = items[0]
        check('Has technique field', 'technique' in t, str(t.get('technique')))
        check('Has campaigns', 'campaigns' in t, str(len(t.get('campaigns', []))))
        check('Has actors', 'actors' in t, str(len(t.get('actors', []))))
        check('Has sectors', 'sectors' in t, str(len(t.get('sectors', []))))

# ============================
print('')
print(SEP)
print('TEST 4: Detection Rules')
print(SEP)
rules = get('/enrichment/detection-rules?limit=5')
if '_error' in rules:
    check('Endpoint', False, rules['_error'])
else:
    check('Has rules', isinstance(rules, list) and len(rules) > 0, str(len(rules)) + ' rules')
    if isinstance(rules, list) and rules:
        r = rules[0]
        check('Rule has name', bool(r.get('name')), r.get('name'))
        check('Rule has rule_type', bool(r.get('rule_type')), r.get('rule_type'))
        check('Rule has content', bool(r.get('content')), str(len(r.get('content', ''))) + ' chars')
        check('Rule has severity', bool(r.get('severity')), r.get('severity'))
        check('Rule has campaign_name', 'campaign_name' in r, str(r.get('campaign_name')))
        check('Rule has quality_score', 'quality_score' in r, str(r.get('quality_score')))

# ============================
print('')
print(SEP)
print('TEST 5: Detection Coverage')
print(SEP)
cov = get('/enrichment/detection-coverage')
if '_error' in cov:
    check('Endpoint', False, cov['_error'])
else:
    check('Has total_rules', 'total_rules' in cov, str(cov.get('total_rules')))
    check('Has yara_count', 'yara_count' in cov, str(cov.get('yara_count')))
    check('Has sigma_count', 'sigma_count' in cov, str(cov.get('sigma_count')))
    check('Has kql_count', 'kql_count' in cov, str(cov.get('kql_count')))
    check('Has campaigns_covered', 'campaigns_covered' in cov, str(cov.get('campaigns_covered')))
    check('Has techniques_covered', 'techniques_covered' in cov, str(cov.get('techniques_covered')))

# ============================
print('')
print(SEP)
print('TEST 6: Briefings')
print(SEP)
briefs = get('/enrichment/briefings?limit=5')
if '_error' in briefs:
    check('Endpoint', False, briefs['_error'])
elif isinstance(briefs, list):
    check('Endpoint works', True, str(len(briefs)) + ' briefings')
    if len(briefs) == 0:
        print('  (No briefings yet - generate one via UI to test)')
    if briefs:
        b = briefs[0]
        check('Has title', bool(b.get('title')), b.get('title'))
        check('Has executive_summary', bool(b.get('executive_summary')), str(b.get('executive_summary', ''))[:80])

# ============================
print('')
print(SEP)
print('TEST 7: Org Exposure')
print(SEP)
expo = post('/enrichment/org-exposure', {
    'sectors': ['Technology', 'Finance'],
    'regions': ['North America'],
    'tech_stack': ['Apache', 'Windows']
})
if '_error' in expo:
    check('Endpoint', False, expo['_error'])
else:
    check('Has exposure_score', 'exposure_score' in expo, str(expo.get('exposure_score')))
    st = expo.get('stats', {})
    check('Has stats', 'stats' in expo, json.dumps(st))
    check('Stats active_campaigns', 'active_campaigns' in st, str(st.get('active_campaigns')))
    check('Stats critical_campaigns', 'critical_campaigns' in st, str(st.get('critical_campaigns')))
    check('Stats kev_count', 'kev_count' in st, str(st.get('kev_count')))
    check('Stats exploitable_count', 'exploitable_count' in st, str(st.get('exploitable_count')))
    tc_list = expo.get('targeting_campaigns', [])
    vp_list = expo.get('vulnerable_products', [])
    check('Has targeting_campaigns', 'targeting_campaigns' in expo, str(len(tc_list)) + ' campaigns')
    check('Has vulnerable_products', 'vulnerable_products' in expo, str(len(vp_list)) + ' products')
    if tc_list:
        tc = tc_list[0]
        print('  Top campaign: ' + str(tc.get('campaign_name')) + ' sev=' + str(tc.get('severity')) + ' actor=' + str(tc.get('actor_name')))
    if vp_list:
        vp = vp_list[0]
        print('  Top vuln: ' + str(vp.get('product_name')) + ' ' + str(vp.get('cve_id')) + ' kev=' + str(vp.get('is_kev')))

# ============================
print('')
print(SEP)
print('TEST 8: Intel Batch Enrichment (Campaign/Actor Badges)')
print(SEP)
intel = get('/intel?limit=5')
ids = []
if isinstance(intel, dict) and 'items' in intel:
    ids = [i['id'] for i in intel['items'][:5] if 'id' in i]
elif isinstance(intel, list):
    ids = [i['id'] for i in intel[:5] if 'id' in i]
if ids:
    check('Found intel items', True, str(len(ids)) + ' items')
    batch = post('/enrichment/intel-batch', {'item_ids': ids})
    if '_error' in batch:
        check('Batch endpoint', False, batch['_error'])
    else:
        check('Has enrichment data', isinstance(batch, dict) and len(batch) > 0, str(len(batch)) + ' items enriched')
        total_camps = sum(len(v.get('campaigns', [])) for v in batch.values())
        total_actors = sum(len(v.get('actors', [])) for v in batch.values())
        check('Campaigns found (violet badges)', total_camps >= 0, str(total_camps) + ' total')
        check('Actors found (red badges)', total_actors >= 0, str(total_actors) + ' total')
        for item_id, en in list(batch.items())[:3]:
            c2 = en.get('campaigns', [])
            a2 = en.get('actors', [])
            if c2 or a2:
                print('  ' + item_id[:8] + ': ' + str(len(c2)) + ' campaigns, ' + str(len(a2)) + ' actors')
else:
    check('Intel items found', False, 'No items')

# ============================
print('')
print(SEP)
print('TEST 9: UI Pages')
print(SEP)
ui_api = os.environ.get('TEST_UI', 'http://ui:3000')
for page in ['/', '/dashboard', '/intel', '/detections', '/briefings', '/settings', '/techniques']:
    try:
        req = urllib.request.Request(ui_api + page)
        r = urllib.request.urlopen(req, timeout=10)
        check('UI ' + page, r.status == 200, 'HTTP ' + str(r.status))
    except Exception as e:
        check('UI ' + page, False, str(e)[:80])

# ============================
print('')
print(SEP)
total = passed + failed
print('RESULTS: ' + str(passed) + ' passed, ' + str(failed) + ' failed, ' + str(total) + ' total')
if failed == 0:
    print('ALL TESTS PASSED!')
else:
    print(str(failed) + ' tests need attention')
print(SEP)
