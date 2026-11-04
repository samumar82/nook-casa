from datetime import datetime,timedelta
from pathlib import Path
import sys,io
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'nook_casa'))
import server as s
now=datetime(2026,11,4,10,0,tzinfo=s.TZ)
assert [s.collection_label(now.date()+timedelta(days=i),now.date()) for i in range(3)] == ['Today','Tomorrow','Day after tomorrow']
assert s.collection_label(now.date()+timedelta(days=6),now.date())=='Tuesday 10 November'
assert s.display_interval(now,{'force':'on'})==60
assert s.display_interval(now,{'force':'off'})==900
assert s.display_interval(now,{'force':'off','_fast_poll':True})==60
night=now.replace(hour=23)
assert s.display_interval(night,{'force':'on'})==60
assert s.display_interval(night,{'force':'off'})==7200
for condition in s.WORDS:
    im=Image.new('L',(120,90),255)
    s.weather_icon(im,(0,0,110,80),condition)
    assert im.getextrema()[0] < 50,condition
for name in ('Paper','Plastic','Glass','Organic','Residual','Metal cans','Garden','Paper + Glass','Unrecognized collection'):
    im=Image.new('L',(600,800),255);s.waste_icons(im,name)
    assert im.crop((450,630,578,715)).getextrema()[0]<50,name
for state,expected in [('on',0),('off',255),('unavailable',255)]:
    im=Image.open(io.BytesIO(s.render({'force':state},now,60)))
    assert im.getpixel((425,485))==expected,state
print('PASS: relative collection labels, active-cycle polling, weather/waste icons and ACS state fill')
