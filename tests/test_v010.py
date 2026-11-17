"""Nook Casa 0.10.0 smoke tests: real renderer geometry, warning conditions."""
from datetime import datetime, timedelta
from pathlib import Path
import io
import sys
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'nook_casa'))
import server as s

now=datetime(2026,11,17,10,30,tzinfo=s.TZ)
sample={
    'occasion':'Santa Elisabetta d’Ungheria', 'aqi':42,
    'nook07_allergens':'bassa', 'nook10_allergen_place':'Casa',
    'nook07_agenda':[{'start':now+timedelta(days=2),
                       'title':'Appuntamento di prova', 'all_day':False}],
    'nook07_alerts':[('SCIOPERI','Sciopero 20/11: ferrovie e TPL (nazionale)')],
    'nook08_dpc_today':'green',
    'nook09_ev_range':410,
    'nook10_day_charge':0.02, 'nook10_day_discharge':0.27,
    'soc':'76','solar':'4.5','grid':'1.1','consumption':'9.8',
    'spanky':'83','acs':'45.5','force':'off','holiday':'off',
    'operation':'Space heating','nook_battery':87,
    'waste_name':'Carta e cartone', 'waste_date':'domani',
    'news':{'text':'Notizia di prova: aggiornamento del servizio', 'unavailable':False},
    'forecast':[{'datetime':(now+timedelta(days=i)).isoformat(),
                 'condition':c, 'temperature':14+i, 'templow':6+i}
                for i,c in enumerate(('sunny','partlycloudy','cloudy','rainy'))],
}
for state in ('full','partial','long'):
    data=dict(sample)
    if state=='partial':
        data.update({'aqi':'unavailable','nook09_ev_range':None,
                     'nook07_agenda':[],'nook07_alerts':[], 'nook08_dpc_today':'unknown'})
    if state=='long':
        data['news']={'text':'Titolo molto lungo. '*180,'unavailable':False}
        data['waste_name']='Imballaggi in carta cartone plastica vetro e altro'
    png=s.render(data, now, 900)
    im=Image.open(io.BytesIO(png))
    assert im.size==(600,800), (state, im.size)
    assert im.mode=='L'
    assert im.getextrema()[0]<40
    visual=im.rotate(-90,expand=True)
    assert visual.size==(800,600)
# Verify the energy readouts are rendered in the home-battery half of the card.
with_energy=s.render(sample,now,900)
without_energy=s.render(dict(sample,nook10_day_charge=None,nook10_day_discharge=None),now,900)
shown=Image.open(io.BytesIO(with_energy)).rotate(-90,expand=True)
hidden=Image.open(io.BytesIO(without_energy)).rotate(-90,expand=True)
assert shown.crop((323,276,408,324)).tobytes() != hidden.crop((323,276,408,324)).tobytes()
assert s.collection_label(now.date()+timedelta(days=1), now.date())=='Domani'
assert s.refresh_interval(now)==900
print('PASS: landscape 800x600 content, legacy PNG 600x800, alerts, empty data, long text and schedule')
