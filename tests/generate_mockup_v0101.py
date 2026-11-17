"""Generate a non-personal, actual-renderer 800x600 Nook Casa mockup."""
from datetime import datetime, timedelta
from pathlib import Path
import io
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'nook_casa'))
import server as s

now = datetime(2026, 11, 17, 15, 10, tzinfo=s.TZ)
def event(day, hour, minute, title):
    return {'start': now.replace(day=day, hour=hour, minute=minute),
            'title': title, 'all_day': False}

demo = {
    'occasion': "Santa Elisabetta d'Ungheria",
    'aqi': '42',
    'nook07_allergens': 'bassa',
    'nook07_agenda': [
        event(19, 7, 45, 'Riunione di progetto e revisione settimanale'),
        event(20, 16, 30, 'Appuntamento di controllo'),
    ],
    'nook07_alerts': [
        ('SCIOPERI', 'Sciopero 20/11: ferrovie e TPL (nazionale)')
    ],
    'nook08_dpc_today': 'green',
    'nook09_ev_range': 410,
    'nook10_day_charge': 0.02,
    'nook10_day_discharge': 0.27,
    'soc': '76',
    'solar': '4.5',
    'grid': '1.1',
    'consumption': '9.8',
    'spanky': '83',
    'acs': '45.5',
    'force': 'off',
    'holiday': 'off',
    'operation': 'Space heating',
    'nook_battery': 87,
    'waste_name': 'Umido',
    'waste_date': 'Oggi',
    'news': {
        'text': 'Aggiornamento dimostrativo sulla viabilita, i trasporti e i servizi locali',
        'unavailable': False,
    },
    'forecast': [
        {'datetime': (now + timedelta(days=i)).isoformat(),
         'condition': cond, 'temperature': 14+i, 'templow': 6+i}
        for i, cond in enumerate(('sunny','partlycloudy','cloudy','rainy'))
    ],
}
png = s.render(demo, now, 900)
portrait = Image.open(io.BytesIO(png))
assert portrait.size == (600, 800), portrait.size
landscape = portrait.rotate(-90, expand=True)
assert landscape.size == (800, 600), landscape.size
out = ROOT / 'docs/images/mockup-landscape-v0101.png'
out.parent.mkdir(parents=True, exist_ok=True)
landscape.save(out, 'PNG', optimize=True)
print('Mockup generated:', out, 'bytes:', out.stat().st_size)
