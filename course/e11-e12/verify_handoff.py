"""Consume locally produced A-stage bytes; never claim A13 delivery."""
import hashlib
import json
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'labs/e11e12'))
from consume_report import consume

out=root/sys.argv[1]
request=json.loads((out/'request.json').read_text())
envelope=out/'incremental-check.json'
payload=out/'incremental-report.json'
metadata=json.loads(envelope.read_text())
result=consume(envelope,hashlib.sha256(envelope.read_bytes()).hexdigest(),
    payload,hashlib.sha256(payload.read_bytes()).hexdigest(),request['repo'],
    request['target'],metadata['job_id'],metadata['trace_id'],root/sys.argv[2],
    source_label='local-e12-rehearsal-not-A13-delivery')
assert result['status']=='SUCCEEDED',result
print(json.dumps({'status':result['status'],'job_id':result['job_id'],
    'trace_id':result['trace_id'],'draft_image_reused':result['draft_image_reused']}))
