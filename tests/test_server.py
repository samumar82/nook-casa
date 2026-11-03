import sys, io, json, threading, urllib.request, urllib.error
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'nook_casa'))
import server as s
from PIL import Image
now=datetime(2026,11,3,19,50,tzinfo=s.TZ)
data={'demo':True,'occasion':'St. Martin de Porres','aqi':'42','operation':'Heating','spanky':'82','soc':'50','consumption':'12.48','solar':'5.5','grid':'1.307','acs':'43.5','force':'off','holiday':'off','waste_name':'Paper and cardboard','waste_date':'Tomorrow 04/11/2026','forecast':[{'datetime':(now+timedelta(days=i)).isoformat(),'condition':c,'temperature':t,'templow':l} for i,(c,t,l) in enumerate([('cloudy',14,7),('rainy',13,8),('partlycloudy',15,6),('sunny',16,5)])]}
png=s.render(data, now,s.refresh_interval(now))
(Path(__file__).resolve().parents[1]/'docs/images/mockup.png').write_bytes(png)
assert Image.open(io.BytesIO(png)).size==(600,800)
edge=s.render({'errors':['weather','waste'],'soc':'unavailable','waste_name':'A waste collection with a very long name '*8},now,1800)
assert Image.open(io.BytesIO(edge)).size==(600,800)
options={'api_key':'test-only-key-012345678901234','device_id':'nook-casa','public_url':'http://127.0.0.1','refresh_seconds':1800}
b=s.Bridge(options)
b.collect=lambda n: data
http=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler);http.bridge=b
options['public_url']='http://127.0.0.1:'+str(http.server_port)
threading.Thread(target=http.serve_forever,daemon=True).start()
base=options['public_url']
try:
    urllib.request.urlopen(base+'/api/display');raise AssertionError('unauthorized accepted')
except urllib.error.HTTPError as e:assert e.code==401
req=urllib.request.Request(base+'/api/display',headers={'ID':'nook-casa','access-token':options['api_key']})
with urllib.request.urlopen(req) as r:
    assert 'no-store' in r.headers['Cache-Control'];meta=json.load(r)
assert 1 <= meta['refresh_rate'] <= 7200
with urllib.request.urlopen(meta['image_url']) as r:assert Image.open(io.BytesIO(r.read())).size==(600,800)
try:
    urllib.request.urlopen(meta['image_url']+'bad');raise AssertionError('bad signature accepted')
except urllib.error.HTTPError as e:assert e.code==403
try:
    urllib.request.urlopen(urllib.request.Request(base+'/force',data=b'{}'));raise AssertionError('control endpoint exists')
except urllib.error.HTTPError as e:assert e.code==404
# Verify daily calendar selection and response envelope against mock HA.
b2=s.Bridge(options)
def ha(path,body=None):
    if path == '/states':return [{'entity_id':e,'state':'off' if e.startswith('switch.') else '50'} for e in s.ENTITIES.values()]
    if path.startswith('/services/weather/'):return {'service_response':{s.WEATHER:{'forecast':data['forecast']}}}
    if path.startswith('/calendars/'):return [{'summary':'Paper','start':{'date':'2026-11-04'},'end':{'date':'2026-11-05'}},{'summary':'Glass','start':{'date':'2026-11-04'},'end':{'date':'2026-11-05'}}]
    raise AssertionError(path)
b2.ha=ha
s.occasion=lambda now: "St. Martin de Porres"
result=b2.collect(now)
assert result['waste_name']=='Paper + Glass' and result['waste_date']=='Tomorrow 04/11/2026'
http.shutdown()
print('PASS: render 600x800, missing data, authentication, signature, cache headers, read-only API, forecast/calendar parsing')
