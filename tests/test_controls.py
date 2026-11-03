import sys,json,threading,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'nook_casa'))
import server as s
options={'api_key':'fixture-only-012345678901234','device_id':'nook-casa','refresh_seconds':1800,'public_url':'http://127.0.0.1'}
b=s.Bridge(options)
states={s.ENTITIES['force']:'off',s.ENTITIES['holiday']:'off'};calls=[]
def ha(path,body=None):
    if path.startswith('/states/'):return {'state':states[path[len('/states/'):]]}
    if path.startswith('/services/switch/'):
        calls.append((path,body));states[body['entity_id']]='on' if path.endswith('turn_on') else 'off';return []
    raise AssertionError(path)
b.ha=ha
http=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler);http.bridge=b
threading.Thread(target=http.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+str(http.server_port)
def post(body,auth=True):
    headers={'Content-Type':'application/json'}
    if auth:headers.update({'ID':options['device_id'],'access-token':options['api_key']})
    request=urllib.request.Request(base+'/api/command',data=json.dumps(body).encode(),headers=headers)
    try:
        with urllib.request.urlopen(request) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.load(e)
assert post({'action':'force_dhw','request_id':'test-id-0001'},False)[0]==401
assert post({'action':'arbitrary_service','request_id':'test-id-0001'})[0]==400
assert post({'action':'holiday_on','request_id':'test-id-0001'})[0]==200
assert states[s.ENTITIES['holiday']]=='on' and len(calls)==1
assert post({'action':'holiday_on','request_id':'test-id-0001'})[0]==200 and len(calls)==1
assert post({'action':'holiday_off','request_id':'test-id-0001'})[0]==409
assert post({'action':'holiday_off','request_id':'test-id-0002'})[0]==200
assert states[s.ENTITIES['holiday']]=='off'
assert post({'action':'force_dhw','request_id':'test-id-0003'})[0]==200
assert states[s.ENTITIES['force']]=='on'
count=len(calls)
assert post({'action':'force_dhw','request_id':'test-id-0004'})[0]==200 and len(calls)==count
b.updated=1234
assert post({'action':'refresh','request_id':'test-id-0005'})[0]==200 and b.updated==0
states[s.ENTITIES['force']]='unavailable'
assert post({'action':'force_dhw','request_id':'test-id-0006'})[0]==502
assert len(calls)==count
http.shutdown()
print('PASS: auth, strict commands, explicit ON/OFF, duplicate protection, idempotent ACS, refresh invalidation, unavailable states')
