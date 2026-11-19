"""Test the DB pipeline endpoint."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
app = create_app()
client = app.test_client()

resp = client.post('/api/academic/db-pipeline/1')
data = json.loads(resp.data)

print('Status:', resp.status_code)
print('Course:', data.get('course_name'))
print('Error:', data.get('error'))
print()
print('Stage log:')
for s in data.get('stage_log', []):
    sym = 'OK ' if s['status'] == 'success' else ('ERR' if s['status'] == 'failed' else '...')
    msg = s.get('message', s.get('error', ''))[:80]
    print(f"  [{sym}] {s['stage']}: {msg}")

print()
print('Topics:', len(data.get('topic_performance') or []))
print('At-risk:', len(data.get('at_risk_students') or []))
print('Gaps:', len(data.get('gaps') or []))
co = data.get('co_attainment') or {}
print('CO attainment overall:', co.get('overall_attainment_pct'))
print('Support plan status:', (data.get('support_plan') or {}).get('_generation_status'))
print()
print('ALL OK' if resp.status_code == 200 else 'FAILED')
