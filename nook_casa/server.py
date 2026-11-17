"""HA -> PNG bridge with authenticated, allowlisted Ecodan commands."""
from html.parser import HTMLParser
import html
import hashlib
import hmac
import io
import json
import logging
import math
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlsplit, parse_qs
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

TZ = ZoneInfo("Europe/Rome")

def refresh_interval(now):
    """Day/night cadence, shortened to wake at the next local boundary."""
    now = now.astimezone(TZ)
    morning = now.replace(hour=7, minute=0, second=0, microsecond=0)
    evening = now.replace(hour=20, minute=30, second=0, microsecond=0)
    if morning <= now < evening:
        interval, boundary = 900, evening
    else:
        interval = 7200
        boundary = morning if now < morning else morning + timedelta(days=1)
    remaining = boundary.timestamp() - now.timestamp()
    return max(1, min(interval, int(remaining + 0.999999)))

ENTITIES = {
    "soc": "sensor.batteries_state_of_capacity",
    "solar": "sensor.inverter_daily_yield",
    "grid": "sensor.grid_import_today",
    "consumption": "sensor.home_consumption_today",
    "acs": "sensor.ecodan_heatpump_dhw_current_temp",
    "force": "switch.ecodan_heatpump_force_dhw",
    "holiday": "switch.ecodan_heatpump_holiday_mode",
    "operation": "sensor.ecodan_heatpump_operation_mode",
    "aqi": "sensor.air_quality_index",
    "spanky": "sensor.xpeng_battery",
}
WEATHER = "weather.home"
CALENDAR = "calendar.waste_collection"
WORDS = {"sunny":"Sunny", "clear-night":"Clear", "partlycloudy":"Partly cloudy",
    "cloudy":"Cloudy", "rainy":"Rain", "pouring":"Heavy rain",
    "lightning-rainy":"Thunderstorms", "lightning":"Thunderstorms", "snowy":"Snow",
    "snowy-rainy":"Sleet", "fog":"Fog", "windy":"Windy",
    "windy-variant":"Windy", "hail":"Hail", "exceptional":"Variable"}
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

def num(value, digits=1, suffix=""):
    try:
        v = float(value)
        if not math.isfinite(v):
            return "--"
        return f"{v:.{digits}f}" + suffix
    except (ValueError, TypeError):
        return "--"

def parse_date(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)

def font(size, bold=False):
    family = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(family, size)

def weather_icon(im, bounds, condition):
    """Draw high-contrast weather symbols without external fonts or assets."""
    from PIL import ImageFilter
    x, y, w, h = bounds
    tile = Image.new('L', (110, 80), 255)
    d = ImageDraw.Draw(tile)
    known = {'sunny','clear-night','partlycloudy','cloudy','rainy','pouring','lightning','lightning-rainy','snowy','snowy-rainy','fog','windy','windy-variant','hail','exceptional'}
    if condition not in known:
        d.text((39, 12), '?', font=font(42, True), fill=0)
    else:
        if condition in ('sunny','partlycloudy','exceptional'):
            cx, cy = (53,38) if condition == 'sunny' else (34,26)
            for angle in range(0,360,45):
                a = math.radians(angle)
                d.line((cx+22*math.cos(a),cy+22*math.sin(a),cx+30*math.cos(a),cy+30*math.sin(a)),fill=0,width=3)
            d.ellipse((cx-16,cy-16,cx+16,cy+16),outline=0,width=3)
        if condition == 'clear-night':
            d.ellipse((30,8,78,60),fill=0)
            d.ellipse((45,2,88,48),fill=255)
        if condition in ('windy','windy-variant','fog'):
            for yy, end in ((24,87),(39,99),(54,79)):
                d.line((16,yy,end,yy),fill=0,width=4)
                if condition != 'fog': d.arc((end-16,yy-14,end+3,yy),180,360,fill=0,width=3)
        if condition not in ('sunny','clear-night','windy','windy-variant','fog'):
            mask=Image.new('L',tile.size,0);m=ImageDraw.Draw(mask)
            m.ellipse((21,27,54,57),fill=255);m.ellipse((39,14,78,58),fill=255)
            m.ellipse((66,29,94,57),fill=255);m.rectangle((36,38,81,57),fill=255)
            tile.paste(0,(0,0),mask.filter(ImageFilter.MaxFilter(7)))
            tile.paste(255,(0,0),mask);d=ImageDraw.Draw(tile)
            if condition in ('rainy','pouring','lightning-rainy','snowy-rainy'):
                for xx in (32,53,74):d.line((xx,65,xx-5,76),fill=0,width=3)
                if condition == 'pouring':
                    for xx in (42,63,84):d.line((xx,64,xx-5,75),fill=0,width=2)
            if condition in ('snowy','snowy-rainy','hail'):
                for xx in (31,57,81):
                    if condition == 'hail':d.ellipse((xx-2,67,xx+2,71),fill=0)
                    else:
                        d.line((xx-4,70,xx+4,70),fill=0,width=2)
                        d.line((xx,66,xx,74),fill=0,width=2)
                        d.line((xx-3,67,xx+3,73),fill=0,width=2)
            if condition in ('lightning','lightning-rainy'):
                d.polygon(((58,45),(46,65),(57,65),(48,79),(73,58),(61,58),(69,45)),fill=0)
    im.paste(tile.resize((w,h),Image.Resampling.LANCZOS),(x,y))

def waste_icons(im, name):
    """Match common collection names and draw compact monochrome material symbols."""
    value=str(name).lower()
    groups=[('paper',('carta','cartone','paper','cardboard')),('plastic',('plastica','plastic','imballaggi','packaging')),('glass',('vetro','glass')),('organic',('umido','organico','organic','food waste')),('residual',('secco','indifferenziato','residuo','residual','general waste')),('metal',('lattine','metalli','metal','cans')),('garden',('verde','sfalci','garden'))]
    kinds=[key for key,terms in groups if any(term in value for term in terms)]
    if not kinds or len(kinds)>2:kinds=['mixed']
    for i,kind in enumerate(kinds):
        tile=Image.new('L',(64,82),255);d=ImageDraw.Draw(tile)
        if kind=='paper':
            d.rectangle((10,13,43,61),outline=0,width=3)
            d.polygon(((20,7),(43,7),(54,18),(54,66),(20,66)),fill=255,outline=0,width=3)
            d.line((43,7,43,19,54,19),fill=0,width=2)
            for yy in (28,37,46,55):d.line((27,yy,47,yy),fill=0,width=2)
        elif kind in ('plastic','glass'):
            d.polygon(((27,8),(39,8),(39,21),(46,28),(46,64),(20,64),(20,28),(27,21)),outline=0,width=3)
            d.rectangle((26,5,40,11),fill=0)
            if kind=='plastic':
                for yy in (34,42,50,58):d.line((22,yy,44,yy),fill=0,width=2)
            else:d.rectangle((24,35,42,50),outline=0,width=2)
        elif kind=='organic':
            d.ellipse((12,25,53,65),outline=0,width=3)
            d.rectangle((28,21,37,30),fill=255)
            d.line((32,28,35,11),fill=0,width=3)
            d.ellipse((37,9,54,20),outline=0,width=2)
            d.line((16,39,18,34),fill=0,width=2)
        elif kind=='metal':
            d.rectangle((17,17,49,60),outline=0,width=3)
            d.ellipse((17,10,49,23),fill=255,outline=0,width=3)
            d.arc((17,53,49,66),0,180,fill=0,width=3)
            d.ellipse((28,13,38,18),outline=0,width=2)
        elif kind=='garden':
            d.ellipse((12,12,52,60),outline=0,width=3)
            d.line((20,66,42,23),fill=0,width=3)
            d.line((29,47,20,32),fill=0,width=2)
            d.line((34,38,47,34),fill=0,width=2)
        else:
            d.polygon(((19,23),(47,23),(43,65),(23,65)),outline=0,width=3)
            d.line((14,20,52,20),fill=0,width=4)
            d.rectangle((25,12,41,19),outline=0,width=3)
            for xx in (29,37):d.line((xx,31,xx,57),fill=0,width=2)
        width=62 if len(kinds)==2 else 78
        x=450+i*64 if len(kinds)==2 else 486
        im.paste(tile.resize((width,82),Image.Resampling.LANCZOS),(x,631))

def display_interval(now, data):
    # Poll active forced heating more often, including during the night window.
    return min(refresh_interval(now),60) if data.get('force') == 'on' or data.get('_fast_poll') else refresh_interval(now)

def collection_label(day, today):
    delta=(day-today).days
    relative={0: 'Oggi', 1: 'Domani', 2: 'Dopodomani'}
    if delta in relative:return relative[delta]
    return f"{['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica'][day.weekday()]} {day.day} {['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'][day.month-1]}"

def render(data, now, interval):
    im = Image.new('L', (600,800),255);d=ImageDraw.Draw(im)
    def text(x,y,value,size=22,bold=False,width=552):
        value=str(value);f=font(size,bold)
        while value and d.textlength(value,font=f)>width:
            value=value[:-1]
        d.text((x,y),value,font=f,fill=0)
    def aligned(bounds,value,size=18,bold=False,center=False,ink=0):
        x1,y1,x2,y2=bounds;value=str(value);f=font(size,bold)
        while size>12 and d.textlength(value,font=f)>x2-x1-8:
            size-=1;f=font(size,bold)
        while value and d.textlength(value,font=f)>x2-x1-8:value=value[:-1]
        left,top,right,bottom=d.textbbox((0,0),value,font=f)
        xx=(x1+x2-(right-left))/2-left if center else x1-left
        yy=(y1+y2-(bottom-top))/2-top
        d.text((round(xx),round(yy)),value,font=f,fill=ink)
    def line(y):d.line((24,y,576,y),fill=0,width=2)
    def button(bounds,label,active=False,size=18):
        d.rectangle(bounds,fill=0 if active else 255,outline=0,width=2)
        aligned(bounds,label,size,True,True,255 if active else 0)
    weekdays_long=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    months=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    weekdays=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    date_label=f'{weekdays_long[now.weekday()]} {now.day} {months[now.month-1]} {now.year}'
    aligned((24,8,495,44),date_label,27,True)
    aligned((508,8,576,44),num(data.get('nook_battery'),0,'%'),15,True,True)
    aligned((24,48,448,85),data.get('occasion',''),26,True)
    line(96)
    text(24,105,'WEATHER / TODAY + NEXT 3 DAYS',18,True)
    forecasts={}
    for item in data.get('forecast',[]):
        try:forecasts[parse_date(item['datetime']).date()]=item
        except (ValueError,KeyError,TypeError):pass
    for i in range(4):
        day=now.date()+timedelta(days=i);x=24+i*140
        if i:d.line((x-8,141,x-8,258),fill=150)
        text(x,141,'Today' if i==0 else weekdays[day.weekday()]+' '+day.strftime('%d'),22,True,128)
        f=forecasts.get(day,{})
        weather_icon(im,(x+6,174,110,80),f.get('condition'))
        text(x,260,num(f.get('templow'),0)+' / '+num(f.get('temperature'),0)+' °C',19,width=128)
    text(24,292,'AIR QUALITY   AQI '+num(data.get('aqi'),0),19,True)
    line(323)
    text(24,333,'ENERGY / TODAY',18,True)
    metrics=[('HOME BATT.', 'soc', 0, '%'), ('SOLAR', 'solar', 2, ''), ('GRID', 'grid', 2, ''), ('HOME USE', 'consumption', 2, ''), ('XPENG', 'spanky', 0, '%')]
    for i,(label,key,digits,suffix) in enumerate(metrics):
        x=24+i*112
        text(x,362,label,13,True,104)
        text(x,383,num(data.get(key),digits,suffix),27,True,104)
        text(x,417,'battery' if key in ('soc','spanky') else 'kWh',14,width=104)
    line(443)
    text(24,451,'HOT WATER',18,True)
    aligned((24,474,299,532),num(data.get('acs'),1,' °C'),37,True)
    button((416,474,576,532),'HEAT WATER',data.get('force')=='on')
    operation=data.get('operation')
    if operation in (None,'unknown','unavailable'):operation='Unavailable'
    text(24,533,'Operation: '+str(operation),18)
    aligned((24,569,216,603),'HOLIDAY MODE',18,True)
    holiday=data.get('holiday')
    aligned((216,569,416,603),'ENABLED' if holiday=='on' else 'DISABLED' if holiday=='off' else '--',18,True,True)
    button((438,569,576,603),'CHANGE',False,17)
    line(617)
    text(24,633,data.get('waste_name','Unavailable'),28,True,416)
    text(24,679,data.get('waste_date','Calendar unavailable'),25,True)
    waste_icons(im,data.get('waste_name',''))
    line(727)
    next_time=now+timedelta(seconds=interval)
    aligned((24,738,419,770),'Next edition '+next_time.strftime('%H:%M'),18)
    button((438,738,576,770),'REFRESH',False,17)
    text(24,778,('Partial data: '+', '.join(data.get('errors',[]))) if data.get('errors') else 'Updated at '+now.strftime('%H:%M'),11)
    if data.get('demo'):text(390,780,'DEMO',10,True,80)
    out=io.BytesIO();im.save(out,'PNG');return out.getvalue()

class SaintParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []
        self.labels = []
    def handle_starttag(self, tag, attrs):
        if tag == "h2": self.inside, self.parts = True, []
    def handle_data(self, data):
        if self.inside: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == "h2" and self.inside:
            label = " ".join(" ".join(self.parts).split())
            if re.match(r"^(San |Santa |Sant[\'’]|Santi |Sante |Beato |Beata )", label):
                self.labels.append(label[:120])
            self.inside = False

FIXED_OCCASIONS = {
    "01-01":"Capodanno", "01-06":"Epifania", "04-25":"Festa della Liberazione",
    "05-01":"Festa del Lavoro", "06-02":"Festa della Repubblica",
    "08-15":"Ferragosto · Assunzione", "11-01":"Tutti i Santi",
    "12-08":"Immacolata Concezione", "12-25":"Natale", "12-26":"Santo Stefano",
}

def occasion(now):
    fixed = FIXED_OCCASIONS.get(now.strftime("%m-%d"))
    if fixed: return fixed
    cache = Path(os.environ.get("NOOK_SAINT_CACHE", "/data/saint_cache.json"))
    today = now.date().isoformat()
    try:
        saved = json.loads(cache.read_text())
        if saved.get("date") == today: return saved.get("label", "")
    except (OSError, ValueError): pass
    label = ""
    try:
        url = "https://www.vaticannews.va/it/santo-del-giorno/"+now.strftime("%m/%d")+".html"
        req = Request(url, headers={"User-Agent":"NookCasa/0.1 (daily calendar)"})
        with urlopen(req, timeout=3) as response:
            source = response.read(1000000).decode("utf-8", errors="replace")
        parser = SaintParser()
        parser.feed(source)
        if parser.labels: label = parser.labels[0]
    except Exception:
        logging.info("Daily occasion unavailable; leaving the label empty")
    try:
        cache.write_text(json.dumps({"date":today,"label":label}))
    except OSError: pass
    return label


class TelegramNewsParser(HTMLParser):
    """Extract recent public posts from Telegram's channel preview."""
    def __init__(self):
        super().__init__()
        self.messages = []
        self.current = None
        self.text_depth = 0
        self.text_parts = []

    def _finish(self):
        if self.current:
            text_value = ' '.join(' '.join(self.text_parts).split())
            if self.current.get('date') and text_value:
                self.current['text'] = text_value[:1200]
                self.messages.append(self.current)
        self.current, self.text_depth, self.text_parts = None, 0, []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if 'data-post' in props and tag == 'div':
            self._finish()
            self.current = {'id': props['data-post']}
        if self.current is None:
            return
        if tag == 'time' and props.get('datetime'):
            self.current['date'] = props['datetime']
        classes = props.get('class', '')
        if tag == 'div' and 'tgme_widget_message_text' in classes:
            self.text_depth = 1
            return
        if self.text_depth:
            if tag == 'div': self.text_depth += 1
            elif tag == 'br': self.text_parts.append(' ')

    def handle_data(self, data):
        if self.text_depth:
            self.text_parts.append(data)

    def handle_endtag(self, tag):
        if self.text_depth and tag == 'div':
            self.text_depth -= 1

    def close(self):
        super().close()
        self._finish()


class NewsFeed:
    def __init__(self):
        self.checked = 0
        self.item = None
        self.failed = False

    def latest(self, now):
        if not self.checked or time.monotonic() - self.checked >= 120:
            self.checked = time.monotonic()
            try:
                req = Request('https://t.me/s/ultimora',
                              headers={'User-Agent':'Mozilla/5.0 NookCasa/0.10'})
                with urlopen(req, timeout=4) as response:
                    content = response.read(2000001)
                if len(content) > 2000000:
                    raise ValueError('news response too large')
                parser = TelegramNewsParser()
                parser.feed(content.decode('utf-8', errors='replace'))
                parser.close()
                valid = []
                for item in parser.messages:
                    try:
                        age = (now - parse_date(item['date'])).total_seconds()
                        if -300 <= age <= 86400:
                            valid.append(item)
                    except (KeyError, ValueError, TypeError):
                        continue
                self.item = max(valid, key=lambda i: parse_date(i['date'])) if valid else None
                self.failed = False
            except Exception:
                self.failed = True
                logging.info('Ultimora temporaneamente non disponibile')
        item = dict(self.item) if self.item else {}
        if item:
            try:
                if not -300 <= (now-parse_date(item['date'])).total_seconds() <= 86400:
                    item = {}
            except (KeyError, ValueError, TypeError):
                item = {}
        item['unavailable'] = self.failed
        return item


class Bridge:
    def __init__(self, options):
        self.options = options
        self.news_feed = NewsFeed()
        self.entities = {key: options.get("entity_" + key, entity) for key, entity in ENTITIES.items()}
        self.weather = options.get("weather_entity", WEATHER)
        self.calendar = options.get("waste_calendar", CALENDAR)
        self.lock = threading.Lock()
        self.image = b""
        self.revision = ""
        self.updated = 0
        self.last_contact = None
        self.nook_battery = None
        self.force_active = False
        self.fast_poll_until = 0
        self.command_lock = threading.Lock()
        self.requests = {}
        self.token = os.environ.get("SUPERVISOR_TOKEN", "")
        self.api = os.environ.get("NOOK_HA_API", "http://supervisor/core/api").rstrip("/")

    def ha(self, path, body=None):
        req = Request(self.api + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization":"Bearer " + self.token, "Content-Type":"application/json"})
        with urlopen(req, timeout=4) as resp:
            return json.load(resp)

    def collect(self, now):
        data = {"errors":[]}
        try:
            selected = set(self.entities.values())
            states = {s["entity_id"]:s.get("state") for s in self.ha("/states")
                      if s.get("entity_id") in selected}
        except Exception:
            states = {}
        for key, entity in self.entities.items():
            data[key] = states.get(entity)
            if data[key] in ("unknown", "unavailable", None): data["errors"].append(key)
        try:
            r = self.ha("/services/weather/get_forecasts?return_response", {"entity_id":self.weather,"type":"daily"})
            data["forecast"] = r["service_response"][self.weather]["forecast"]
        except Exception:
            data["errors"].append("weather")
        try:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query = urlencode({"start":start.isoformat(),"end":(start+timedelta(days=30)).isoformat()})
            events = self.ha("/calendars/" + self.calendar + "?" + query)
            # Today's all-day collection stays visible through today; expired timed events do not.
            def relevant(e):
                end = e.get("end", {})
                if isinstance(end, dict): end = end.get("dateTime", end.get("date"))
                return parse_date(end) > now
            def start_dt(e):
                s = e["start"]
                if isinstance(s, dict): s = s.get("dateTime", s.get("date"))
                return parse_date(s)
            events = sorted((e for e in events if relevant(e)), key=start_dt)
            if events:
                first = start_dt(events[0])
                same = [e for e in events if start_dt(e).date() == first.date()]
                data["waste_name"] = " + ".join(dict.fromkeys(e.get("summary", "Collection") for e in same))
                data["waste_date"] = collection_label(first.date(), now.date())
            else:
                data["waste_name"] = "No collection in the next 30 days"
                data["waste_date"] = "Check the waste collection calendar"
        except Exception:
            data["errors"].append("waste")
        data["occasion"] = occasion(now)
        data["news"] = self.news_feed.latest(now)
        return data

    def refresh(self):
        with self.lock:
            if self.image and time.time()-self.updated < 45: return
            now = datetime.now(TZ)
            data = dict(self.collect(now))
            data["nook_battery"] = self.nook_battery
            data["_fast_poll"] = time.time() < self.fast_poll_until
            self.force_active = data.get("force") == "on"
            self.image = render(data, now, display_interval(now, data))
            self.revision = hashlib.sha256(self.image).hexdigest()[:20]
            self.updated = time.time()
            logging.info("Page generated; missing data: %s", ",".join(data.get("errors", [])) or "none")

    def signature(self, rev, expires):
        return hmac.new(self.options["api_key"].encode(), f"{rev}:{expires}".encode(), hashlib.sha256).hexdigest()


"""Add read-only HA data to Nook Casa 0.6.0; preserve existing collector."""

def _nook07_short(s, limit=110):
    return ' '.join(str(s or '').replace('\n', ' ').split())[:limit]


def _nook07_fetch_event_date(item, key):
    value = item.get(key) or {}
    if isinstance(value, dict):
        value = value.get('dateTime') or value.get('date') or ''
    if not value:
        return None
    try:
        return parse_date(value)
    except (ValueError, TypeError):
        return None


def _nook07_collect(self, now, _previous):
    """Supplement old 0.6.0 collector. A failure never breaks old data."""
    data = _previous(self, now)
    data['nook07_agenda'] = []
    data['nook07_alerts'] = []
    data['nook07_allergens'] = None
    data['nook07_agenda_error'] = False
    data['nook08_dpc_today'] = 'unknown'
    data['nook09_ev_range'] = None
    data['nook09_range_entity'] = None
    data['nook10_day_charge'] = None
    data['nook10_day_discharge'] = None
    data['nook07_external_error'] = False

    # HA sensors are already scoped to home: do not infer alerts from national DPC counts.
    try:
        all_states = self.ha('/states')
        by_id = {s['entity_id']: s for s in all_states if 'entity_id' in s}

        # Daily home battery throughput, never instantaneous W or lifetime totals.
        for key, opt, default in (
            ('nook10_day_charge', 'battery_day_charge_entity', 'sensor.batteries_day_charge'),
            ('nook10_day_discharge', 'battery_day_discharge_entity', 'sensor.batteries_day_discharge'),
        ):
            entity_id = str(getattr(self, 'options', {}).get(opt) or default).strip()
            sensor = by_id.get(entity_id) or {}
            unit = str((sensor.get('attributes') or {}).get('unit_of_measurement') or '').lower()
            if unit != 'kwh':
                continue
            try:
                amount = float(sensor.get('state'))
                if math.isfinite(amount) and amount >= 0:
                    data[key] = amount
            except (TypeError, ValueError):
                pass
        def state(eid):
            return by_id.get(eid, {})
        def valid(s):
            return s not in (None, '', 'unknown', 'unavailable')

        pollen_id = getattr(self, 'options', {}).get('allergy_risk_entity') or 'sensor.polleninformation_home_allergy_risk'
        pollen = state(pollen_id)
        if not pollen:
            pollen = next((v for k, v in by_id.items()
                           if k.startswith('sensor.polleninformation_')
                           and k.endswith('_allergy_risk')), {})
        risk = pollen.get('state')
        if valid(risk):
            data['nook07_allergens'] = _nook07_short(risk, 35)
            data['nook10_allergen_place'] = _nook07_short((pollen.get('attributes') or {}).get('location_title') or 'Casa', 35)

        data['nook08_dpc_today'] = state('sensor.dpc_today_alert').get('state') or 'unknown'
        zone = _nook07_short(state('sensor.dpc_alert_zone').get('state'), 65)
        risk_labels = {'yellow': 'gialla', 'orange': 'arancione', 'red': 'rossa'}
        for eid, when in (('sensor.dpc_today_alert', 'Oggi'),
                          ('sensor.dpc_tomorrow_alert', 'Domani')):
            alert_state = str(state(eid).get('state') or '').lower()
            if alert_state in risk_labels:
                summary = 'Protezione Civile: allerta ' + risk_labels[alert_state]
                summary += ' (' + when.lower() + ')'
                if zone and valid(zone):
                    summary += ' · ' + zone
                data['nook07_alerts'].append(('DPC', summary))

        # XPENG: use actual remaining-range sensor in kilometres, never infer
        # range from SOC; if no compatible sensor is present show "— km".
        # Prefer user-configured choice if specified via environment.
        configured = str(getattr(self, 'options', {}).get('ev_range_entity') or os.environ.get('NOOK_XPENG_RANGE_ENTITY') or '').strip()
        range_candidates = []
        for eid, val in by_id.items():
            if not eid.startswith('sensor.xpeng_'):
                continue
            if configured and eid != configured:
                continue
            state_val = val.get('state')
            attrs = val.get('attributes') or {}
            combined = (eid + ' ' + str(attrs.get('friendly_name') or '')).lower()
            if not any(term in combined for term in ('range', 'autonomia', 'distance_to_empty', 'remaining_mileage')):
                continue
            if any(term in combined for term in ('trip', 'odometer', 'charge_limit', 'charged', 'range_since', 'range_at_')):
                continue
            if str(attrs.get('unit_of_measurement') or '').lower() not in ('km','kilometer','kilometers'):
                continue
            try:
                km = float(state_val)
                if not math.isfinite(km) or not (0 <= km <= 1500):continue
            except (ValueError, TypeError):
                continue
            score = 0
            for term, pts in (('remaining_range',40),('remaining_distance',35),('estimated_range',30),
                              ('driving_range',25),('distance_to_empty',25),('range',10),('autonomia',10)):
                if term in combined: score += pts
            if 'wltp' in combined or 'rated' in combined: score -= 15
            if 'dynamic' in combined: score += 6
            range_candidates.append((score, eid, km))
        if range_candidates:
            range_candidates.sort(key=lambda x:(-x[0],x[1]))
            _,eid,km = range_candidates[0]
            data['nook09_ev_range'] = km
            data['nook09_range_entity'] = eid

        # The local-strikes integration already respects the HA home location.
        nearby = state('sensor.scioperi_vicini').get('attributes', {}).get('strikes', [])
        candidates = nearby if isinstance(nearby, list) else []
        next_local = state('sensor.scioperi_prossimo_vicino')
        if not candidates and next_local:
            candidates = [next_local.get('attributes', {})]
        future = []
        for strike in candidates:
            if not isinstance(strike, dict):
                continue
            try:
                day = datetime.strptime(strike.get('start_date', ''), '%d/%m/%Y').date()
            except (ValueError, TypeError):
                continue
            delta = (day - now.date()).days
            if not (0 <= delta <= 5):
                continue
            sector = _nook07_short(strike.get('sector', 'trasporti'), 45)
            modality = str(strike.get('modality') or '').lower()
            if 'ferroviar' in modality and ('tpl' in modality or 'trasporto pubblico' in modality):
                sector = 'ferrovie e TPL'
            elif 'ferroviar' in modality:
                sector = 'ferrovie'
            if strike.get('distance') == 'Nazionale':
                region = 'nazionale'
            else:
                region = _nook07_short(strike.get('region') or 'zona', 32)
            when = 'oggi' if delta == 0 else 'domani' if delta == 1 else day.strftime('%d/%m')
            future.append((day, 'Sciopero ' + when + ': ' + sector + ' (' + region + ')'))
        if future:
            future.sort(key=lambda item: item[0])
            data['nook07_alerts'].append(('SCIOPERI', future[0][1]))
    except Exception:
        data['nook07_external_error'] = True
        logging.exception('Nook 0.7: lettura allergeni/allerta/scioperi non riuscita')

    try:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = urlencode({
            'start': start.isoformat(),
            'end': (start + timedelta(days=8)).isoformat(),
        })
        agenda_id = getattr(self, 'options', {}).get('agenda_calendar') or 'calendar.home'
        events = self.ha('/calendars/' + agenda_id + '?' + query)
        agenda = []
        for event in events:
            begin = _nook07_fetch_event_date(event, 'start')
            end = _nook07_fetch_event_date(event, 'end')
            if not begin or (end and end <= now):
                continue
            if begin.date() < now.date():
                begin = now
            original_start = event.get('start') or {}
            all_day = isinstance(original_start, dict) and 'date' in original_start and 'dateTime' not in original_start
            agenda.append({'start': begin, 'title': _nook07_short(event.get('summary'), 100), 'all_day': all_day})
        data['nook07_agenda'] = sorted(agenda, key=lambda item: item['start'])[:2]
    except Exception:
        data['nook07_agenda_error'] = True
        logging.exception('Nook 0.7: agenda personale non disponibile')
    return data



"""Nook Casa horizontal final renderer v0.10 — compatible with old client.

Expected input: data from 0.6.0 + supplement from v0.7, optionally:
  nook09_ev_range (from verified HA sensor)
Output: PNG 600x800 (landscape logical 800x600 rotated 90 degrees for legacy client).
All UI is informational and touch-free.
"""

# NOOK_CASA_LANDSCAPE_V10_RENDER_START

def _nook10_render(data, now, interval):
    from PIL import Image, ImageDraw
    from datetime import timedelta
    import io, math

    W,H=800,600
    im=Image.new('L',(W,H),255)
    d=ImageDraw.Draw(im)
    INK=9
    CHAR=30
    SOFT=120
    LIGHT=192
    REGULAR={}

    def F(size,bold=False):
        k=(size,bold)
        if k not in REGULAR: REGULAR[k]=font(size,bold)
        return REGULAR[k]
    def fit(s,size,max_w,bold=False):
        s=' '.join(str(s if s is not None else '—').split())
        f=F(size,bold)
        if d.textlength(s,font=f) <= max_w: return s
        while s and d.textlength(s+'…',font=f)>max_w: s=s[:-1]
        return s.rstrip(' .')+'…' if s else '—'
    def txt(x,y,s,sz=16,bold=False,max_w=780,color=INK):
        # Font +1 px below the first two header lines; preserve original ink.
        if y >= 87: sz += 1
        s=fit(s,sz,max_w,bold)
        d.text((x,y),s,font=F(sz,bold),fill=color)
    def right(x,y,s,sz=14,bold=False,color=INK):
        s=str(s)
        d.text((round(x-d.textlength(s,font=F(sz,bold))),y),s,font=F(sz,bold),fill=color)
    def card(box,r=11,thick=2):
        d.rounded_rectangle(box,radius=r,outline=CHAR,width=thick)
    def hline(x1,y,x2,shade=SOFT,width=1):d.line((x1,y,x2,y),fill=shade,width=width)
    def vline(x,y1,y2,shade=SOFT,width=1):d.line((x,y1,x,y2),fill=shade,width=width)
    def fmt(value,digits=0):
        val=num(value,digits)
        return val.replace('.',',') if val!='--' else '—'
    def valid(v):return v not in ('unknown','unavailable',None,'')

    def ic_suncloud(x,y,w=60,h=50,kind='partlycloudy',stroke=3):
        # Outlines intentionally simple and high-contrast on physical e-ink.
        cond=str(kind or '').lower()
        rainy=cond in ('rainy','pouring','lightning-rainy','snowy-rainy')
        only_sun=cond in ('sunny','clear-night')
        if cond in ('sunny','partlycloudy','exceptional','clear-night'):
            cx,cy=x+w*.62,y+h*.33
            R=min(w,h)*.16
            d.ellipse((cx-R,cy-R,cx+R,cy+R),outline=INK,width=stroke)
            for deg in range(0,360,45):
                rad=math.radians(deg)
                a,b=R+4,R+10
                d.line((cx+math.cos(rad)*a,cy+math.sin(rad)*a,cx+math.cos(rad)*b,cy+math.sin(rad)*b),fill=INK,width=max(2,stroke-1))
        if not only_sun:
            xa=x+w*.12;yb=y+h*.81
            d.ellipse((xa,yb-h*.37,xa+w*.38,yb),outline=INK,width=stroke,fill=255)
            d.ellipse((xa+w*.22,yb-h*.62,xa+w*.69,yb),outline=INK,width=stroke,fill=255)
            d.ellipse((xa+w*.51,yb-h*.39,xa+w*.85,yb),outline=INK,width=stroke,fill=255)
            d.line((xa+w*.16,yb,xa+w*.70,yb),fill=INK,width=stroke)
            if rainy:
                for i in (0.29,0.51,0.69):
                    xx=xa+w*i
                    d.line((xx,yb+4,xx-4,yb+10),fill=INK,width=2)
        if only_sun and cond=='clear-night':
            pass

    def ic_leaf(x,y,s=33):
        d.ellipse((x+5,y+2,x+s-4,y+s-6),outline=INK,width=3)
        d.line((x+7,y+s-3,x+s-6,y+7),fill=INK,width=3)
        d.line((x+15,y+20,x+9,y+15),fill=INK,width=2)
    def ic_flower(x,y,s=33):
        cx,cy=x+s/2,y+s/2; rr=s*.17
        for angle in range(0,360,72):
            a=math.radians(angle)
            ex,ey=cx+math.cos(a)*s*.28,cy+math.sin(a)*s*.28
            d.ellipse((ex-rr,ey-rr,ex+rr,ey+rr),outline=INK,width=2,fill=255)
        d.ellipse((cx-4,cy-4,cx+4,cy+4),fill=INK)
    def ic_solar(x,y,s=48):
        d.polygon([(x+11,y+5),(x+s-10,y+5),(x+s-2,y+s*.70),(x+2,y+s*.70)],outline=INK,width=3)
        for f in (.35,.65):d.line((x+9+s*.64*f,y+6,x+3+s*.89*f,y+s*.70),fill=INK,width=2)
        d.line((x+7,y+s*.44,x+s-6,y+s*.44),fill=INK,width=2)
        d.line((x+s*.5,y+s*.70,x+s*.5,y+s-4),fill=INK,width=3)
        d.line((x+s*.3,y+s-4,x+s*.7,y+s-4),fill=INK,width=3)
    def ic_bolt(x,y,s=43):
        pts=[(x+s*.50,y+1),(x+s*.19,y+s*.52),(x+s*.48,y+s*.52),(x+s*.39,y+s-1),(x+s*.84,y+s*.37),(x+s*.54,y+s*.37)]
        d.polygon(pts,fill=255,outline=INK,width=3)
    def ic_grid(x,y,s=45):
        d.line([(x+2,y+s*.41),(x+s*.49,y+4),(x+s-2,y+s*.41)],fill=INK,width=3,joint='curve')
        d.line([(x+10,y+s*.40),(x+10,y+s-3),(x+s*.73,y+s-3),(x+s*.73,y+s*.40)],fill=INK,width=3)
        d.line([(x+s*.51,y+s*.62),(x+s*.94,y+s*.62)],fill=INK,width=3)
        d.line([(x+s*.80,y+s*.49),(x+s*.94,y+s*.62),(x+s*.8,y+s*.75)],fill=INK,width=3)
    def ic_battery(x,y,w=45,h=27,pct=None):
        d.rounded_rectangle((x,y,x+w-6,y+h),radius=3,outline=INK,width=3)
        d.rectangle((x+w-6,y+8,x+w,y+h-8),fill=INK)
        try:p=max(0,min(100,float(pct)))
        except Exception:p=0
        if p>0:
            fillw=(w-13)*p/100
            d.rectangle((x+5,y+5,x+5+fillw,y+h-5),fill=INK)
    def ic_car(x,y,w=53,h=34):
        d.line([(x+7,y+22),(x+15,y+11),(x+38,y+11),(x+48,y+22)],fill=INK,width=3)
        d.rounded_rectangle((x+3,y+19,x+51,y+32),radius=4,outline=INK,width=3)
        for xx in (x+14,x+41):d.ellipse((xx-5,y+27,xx+5,y+37),fill=255,outline=INK,width=3)
        d.line((x+20,y+12,x+15,y+19),fill=INK,width=2)
    def ic_car_compact(x,y):
        # Bounds 32x20: original ic_car ignores w/h and drew over SOC text.
        d.line([(x+4,y+11),(x+9,y+5),(x+22,y+5),(x+28,y+11)],fill=INK,width=2)
        d.rounded_rectangle((x+2,y+10,x+30,y+16),radius=2,outline=INK,width=2)
        for cx in (x+9,x+24):
            d.ellipse((cx-2,y+15,cx+2,y+19),fill=255,outline=INK,width=1)

    def ic_fan(x,y,s=39):
        cx,cy=x+s/2,y+s/2
        d.ellipse((x+1,y+1,x+s-1,y+s-1),outline=INK,width=2)
        for i in (0,120,240):
            a=math.radians(i)
            px=cx+math.cos(a)*s*.23;py=cy+math.sin(a)*s*.23
            d.ellipse((px-5,py-7,px+5,py+7),outline=INK,width=2)
        d.ellipse((cx-4,cy-4,cx+4,cy+4),fill=INK)
    def ic_drop(x,y,s=39):
        d.polygon([(x+s*.50,y+2),(x+s*.15,y+s*.54),(x+s*.15,y+s*.68),(x+s*.31,y+s*.89),(x+s*.7,y+s*.89),(x+s*.85,y+s*.67),(x+s*.85,y+s*.54)],fill=255,outline=INK,width=3)
        d.arc((x+s*.32,y+s*.54,x+s*.61,y+s*.84),65,165,fill=INK,width=2)
    def ic_waste(x,y,s=35):
        d.rounded_rectangle((x+s*.22,y+s*.29,x+s*.78,y+s*.88),radius=3,outline=INK,width=3)
        d.line((x+3,y+s*.29,x+s-3,y+s*.29),fill=INK,width=3)
        d.line((x+s*.37,y+s*.17,x+s*.63,y+s*.17),fill=INK,width=3)
        for xx in (.39,.6):d.line((x+s*xx,y+s*.40,x+s*xx,y+s*.77),fill=INK,width=2)
    def ic_nook(x,y,w=25,h=40):
        d.rounded_rectangle((x,y,x+w,y+h),radius=3,outline=INK,width=3)
        d.line((x+4,y+5,x+w-4,y+5),fill=SOFT,width=1)
        d.ellipse((x+w/2-2,y+h-5,x+w/2+2,y+h-1),fill=INK)
    def ic_news(x,y,s=19):
        # Keep all strokes within the icon's bounding box. The old 17px
        # variant drew a third line below its outline and into the next row.
        d.rounded_rectangle((x,y,x+s,y+s),radius=2,outline=INK,width=2)
        for off,length in ((5,13),(9,11),(13,9)):
            d.line((x+4,y+off,x+length,y+off),fill=INK,width=2)
    def ic_alert(x,y,s=23):
        d.polygon(((x+s/2,y+1),(x+s-2,y+s-2),(x+2,y+s-2)),outline=INK,width=2)
        d.line((x+s/2,y+8,x+s/2,y+14),fill=INK,width=2)
        d.ellipse((x+s/2-1,y+17,x+s/2+1,y+19),fill=INK)
    def ic_train(x,y,w=23,h=24):
        d.rounded_rectangle((x+3,y,x+w-3,y+h-5),radius=3,outline=INK,width=2)
        d.line((x+6,y+7,x+w-6,y+7),fill=INK,width=2)
        d.line((x+6,y+12,x+w-6,y+12),fill=INK,width=2)
        d.line((x+6,y+h-5,x+3,y+h-1),fill=INK,width=2)
        d.line((x+w-6,y+h-5,x+w-3,y+h-1),fill=INK,width=2)

    # DATE + SAINT: no agenda title or calendar icon here.
    days=['Lunedì','Martedì','Mercoledì','Giovedì','Venerdì','Sabato','Domenica']
    months=['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre']
    short=['Lun','Mar','Mer','Gio','Ven','Sab','Dom']
    txt(23,10,'%s %d %s %d'%(days[now.weekday()],now.day,months[now.month-1],now.year),26,True,558)
    # LDP (last dashboard production/update time) sits at top right.
    # This replaces the bottom footer completely, freeing ~31 px for the feed.
    right(784,16,'LDP '+now.strftime('%d/%m %H:%M'),12,False)
    if data.get('errors') or data.get('nook07_external_error'):
        right(784,42,'Dati parziali',10,False,color=SOFT)
    txt(23,47,data.get('occasion') or '',19,False,740)

    # Top card: next two personal appointments / AQI / local allergens.
    card((12,87,788,164))
    # Agenda widened by 60 px; AQI retains its original 192 px width.
    vline(347,95,156,SOFT)
    vline(539,95,156,SOFT)
    agenda=data.get('nook07_agenda') or []
    if agenda:
        for k,item in enumerate(agenda[:2]):
            date=item['start']
            when=('%s %02d'%(short[date.weekday()],date.day))
            if not item.get('all_day'):when+=' '+date.strftime('%H:%M')
            # Keep time/date visible; title is ellipsized only when unavoidable.
            txt(27,100+k*28,when,15,True,108)
            tw=d.textlength(when,font=F(16,True))
            txt(27+tw+8,100+k*28,item['title'],15,False,max(12,307-tw))
    elif data.get('nook07_agenda_error'):
        txt(26,116,'Calendario non disponibile',15,False,312)
    else:
        txt(26,116,'Nessun impegno nei prossimi 7 giorni',14,False,312)

    ic_leaf(362,106,37)
    txt(408,100,'AQI '+fmt(data.get('aqi')),22,True,122)
    try:
        aqi=float(data.get('aqi'))
        aqi_label='Buona' if 0<=aqi<=50 else 'Moderata' if aqi<=100 else 'Elevata'
    except (ValueError,TypeError):aqi_label='Non disponibile'
    txt(408,132,aqi_label,13,False,120)
    ic_flower(558,107,37)
    pollen=data.get('nook07_allergens') or '—'
    txt(604,100,'Allergeni',18,True,175)
    txt(604,128,str(pollen).capitalize(),17,False,175)

    forecasts={}
    for item in data.get('forecast') or []:
        try:forecasts[parse_date(item['datetime']).date()]=item
        except (ValueError,TypeError,KeyError):pass

    # Columnar body — faithful to the selected mockup.
    card((12,171,161,427))          # Weather forecast column
    card((168,171,654,248))         # Energy
    card((168,253,654,330))         # House / XPENG batteries
    card((168,335,654,427))         # Heat pump & ACS
    card((661,171,788,330))         # Waste
    card((661,335,788,427))         # Nook battery

    for k in range(4):
        date=now.date()+timedelta(days=k)
        yy=178+k*62
        if k:hline(22,yy-5,150,LIGHT)
        f=forecasts.get(date,{})
        ic_suncloud(25,yy+9,46,39,f.get('condition'),2)
        day_label='Oggi' if k==0 else short[date.weekday()]+' '+date.strftime('%d')
        txt(81,yy+4,day_label,16,True,68)
        txt(81,yy+29,fmt(f.get('temperature'))+'° / '+fmt(f.get('templow'))+'°',14,False,68)

    # Three energy cards separated by vertical rules, same data as original.
    for x in (330,492):vline(x,181,239,SOFT)
    ic_solar(178,187,42)
    txt(222,182,fmt(data.get('solar'),2),23,True,102)
    txt(222,216,'FV · kWh',12,False,103)
    ic_bolt(336,190,38)
    txt(374,182,fmt(data.get('consumption'),2),23,True,108)
    txt(374,216,'Consumo · kWh',12,False,110)
    ic_grid(502,186,42)
    txt(544,182,fmt(data.get('grid'),2),23,True,98)
    txt(544,216,'Rete · kWh',12,False,100)

    vline(412,265,319,SOFT)
    # Daily home battery throughput is expressed as energy (kWh), not power.
    ic_battery(180,275,40,27,data.get('soc'))
    txt(230,259,'Batteria casa',14,False,177)
    txt(230,282,fmt(data.get('soc'))+'%',26,True,89)
    charge_today=fmt(data.get('nook10_day_charge'),2)
    discharge_today=fmt(data.get('nook10_day_discharge'),2)
    txt(325,277,'↑ '+charge_today+' kWh',11,False,82)
    txt(325,299,'↓ '+discharge_today+' kWh',11,False,82)
    # Compact icon above two equally sized battery/range values.
    ic_car_compact(426,257)
    txt(465,258,'XPENG',14,False,149)
    xpeng_pct=fmt(data.get('spanky'))+'%'
    range_km=data.get('nook09_ev_range')
    xpeng_km=(fmt(range_km)+' km' if valid(range_km) else '— km')
    ev_x,ev_right,ev_size=424,650,26
    while ev_size>19:
        face=F(ev_size+1,True)
        needed=d.textlength(xpeng_pct,font=face)+10+d.textlength(xpeng_km,font=face)
        if needed<=ev_right-ev_x-2: break
        ev_size-=1
    face=F(ev_size+1,True)
    ev_km_x=round(ev_x+d.textlength(xpeng_pct,font=face)+10)
    txt(ev_x,283,xpeng_pct,ev_size,True,ev_km_x-ev_x-7)
    txt(ev_km_x,283,xpeng_km,ev_size,True,max(10,ev_right-ev_km_x))

    vline(473,346,416,SOFT)
    ic_fan(179,351,37)
    txt(224,342,'PDC',14,True,50)
    operation=data.get('operation')
    if not valid(operation):operation='Non disponibile'
    txt(224,363,str(operation),17,True,233)
    holiday=data.get('holiday')
    holiday_lbl='ON' if holiday=='on' else 'OFF' if holiday=='off' else '—'
    force=data.get('force')
    force_lbl='ON' if force=='on' else 'OFF' if force=='off' else '—'
    txt(178,398,'Holiday Mode: '+holiday_lbl+' · Ciclo ACS: '+force_lbl,13,False,290)
    ic_drop(486,357,39)
    txt(534,345,'ACS',15,True,102)
    txt(534,369,fmt(data.get('acs'),1)+'°C',26,True,112)

    # Waste with a concise date and long-name wrap.
    ic_waste(673,183,34)
    txt(708,184,'Rifiuti',18,True,68)
    hline(672,220,777,SOFT)
    raw=str(data.get('waste_name') or 'Non disponibile')
    pieces=raw.split()
    name_lines=[];cur=''
    for word in pieces:
        test=(cur+' '+word).strip()
        if d.textlength(test,font=F(19,True)) <= 101:cur=test
        else:
            if cur:name_lines.append(cur)
            cur=word
    if cur:name_lines.append(cur)
    waste_name_y=238 if len(name_lines)>1 else 249
    for j,part in enumerate(name_lines[:2]):
        txt(674,waste_name_y+j*22,part,18,True,101)
    waste_date=str(data.get('waste_date') or '—')
    for full,abbr in (('lunedì','Lun'),('martedì','Mar'),('mercoledì','Mer'),('giovedì','Gio'),('venerdì','Ven'),('sabato','Sab'),('domenica','Dom')):
        if waste_date.lower().startswith(full):
            waste_date=abbr+waste_date[len(full):]
            break
    for full,abbr in (('gennaio','gen'),('febbraio','feb'),('marzo','mar'),('aprile','apr'),('maggio','mag'),('giugno','giu'),('luglio','lug'),('agosto','ago'),('settembre','set'),('ottobre','ott'),('novembre','nov'),('dicembre','dic')):
        waste_date=waste_date.replace(full,abbr)
    txt(674,291,waste_date,15,True,101)

    # Nook side panel — no dead touch controls.
    ic_nook(672,351,28,43)
    txt(709,346,'Nook',15,False,64)
    txt(709,369,fmt(data.get('nook_battery'))+'%',23,True,64)

    # News: no heading, no heading icon and NO footer: 5 readable rows.
    # Icons stay entirely inside their own 25px gutter; continuation rows
    # omit the icon so headlines do not collide or repeat pictograms.
    card((12,435,788,591))
    alerts=data.get('nook07_alerts') or []
    dpc=[t for typ,t in alerts if typ=='DPC']
    strikes=[t for typ,t in alerts if typ=='SCIOPERI']
    dpc_state=str(data.get('nook08_dpc_today') or 'unknown').lower()
    if dpc:
        dpc_line=dpc[0]
    elif dpc_state=='green':
        dpc_line='Protezione Civile: nessuna allerta oggi per la zona di casa'
    else:
        dpc_line='Protezione Civile: dati di allerta non disponibili'
    rows=[('dpc', dpc_line)]
    if strikes:
        rows.append(('strikes',strikes[0].replace('Sciopero ','Scioperi: ')))

    news=data.get('news') or {}
    headline=news.get('text')
    if not headline:
        headline=('Notizie momentaneamente non disponibili' if news.get('unavailable',True)
                  else 'Nessuna notizia nelle ultime 24 ore')
    elif news.get('unavailable'):
        headline=str(headline)+' (ultimo dato disponibile)'
    plain='Ultimora: '+' '.join(str(headline).split())
    news_lines_needed=5-len(rows)
    # Word wrapping preserves whole words and leaves room for ellipsis.
    remaining=plain
    for i in range(news_lines_needed):
        if not remaining:break
        face=F(18,False); available=708
        if d.textlength(remaining,font=face)<=available:
            portion=remaining; remaining=''
        else:
            words=remaining.split()
            selected=[]
            for word in words:
                candidate=' '.join(selected+[word])
                if d.textlength(candidate,font=face)<=available:selected.append(word)
                else:break
            portion=' '.join(selected) if selected else fit(remaining,17,available)
            remaining=remaining[len(portion):].lstrip()
        if i == news_lines_needed-1 and remaining:
            portion=fit(portion.rstrip('…')+'…',18,available)
        rows.append(('news' if i==0 else 'continuation', portion))

    for index,(kind,content) in enumerate(rows[:5]):
        y=443+index*29
        if kind=='dpc':ic_alert(27,y+2,20)
        elif kind=='strikes':ic_train(26,y+2,21,22)
        elif kind=='news':ic_news(28,y+3,19)
        txt(62,y,content,17,False,714)

    # The current Nook APK still expects portrait 600x800 bitmap bytes.
    result=im.rotate(90,expand=True)
    out=io.BytesIO();result.save(out,'PNG')
    return out.getvalue()

# NOOK_CASA_LANDSCAPE_V10_RENDER_END


# 0.10.0 portable landscape dashboard (600x800 bitmap, rotated 800x600 page).
_nook10_original_collect = Bridge.collect
def _nook10_bridge_collect(self, now):
    return _nook07_collect(self, now, _nook10_original_collect)
Bridge.collect = _nook10_bridge_collect
render = _nook10_render

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass  # Never log signed URLs or credentials.
    def send(self, code, payload, mime="application/json"):
        if not isinstance(payload, bytes): payload = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(payload)
    def authenticated(self):
        b = self.server.bridge
        return (hmac.compare_digest(self.headers.get("access-token", ""), b.options["api_key"])
                and self.headers.get("ID") == b.options["device_id"])

    def do_POST(self):
        b = self.server.bridge
        if urlsplit(self.path).path != "/api/command":
            return self.send(404, {"error":"not found"})
        if not self.authenticated(): return self.send(401, {"error":"unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024: return self.send(400, {"error":"invalid body"})
            body = json.loads(self.rfile.read(length))
            action = body.get("action")
            request_id = body.get("request_id", "")
            if action not in ("refresh", "force_dhw", "holiday_on", "holiday_off"):
                return self.send(400, {"error":"action not allowed"})
            if not isinstance(request_id,str) or not re.fullmatch(r"[a-zA-Z0-9-]{8,80}",request_id):
                return self.send(400, {"error":"invalid request id"})
        except (ValueError, AttributeError, TypeError):
            return self.send(400, {"error":"invalid request"})
        with b.command_lock:
            b.requests = {k:v for k,v in b.requests.items() if time.time()-v[0] < 600}
            if request_id in b.requests:
                old = b.requests[request_id]
                if old[1] != action: return self.send(409, {"error":"request id reused"})
                return self.send(old[2],old[3])
            # Record before calling HA: a failed response must never duplicate a command.
            b.requests[request_id] = (time.time(),action,409,{"error":"command outcome uncertain; refresh state"})
            try:
                if action == "force_dhw": b.fast_poll_until = time.time()+300
                if action != "refresh":
                    entity = b.entities["force"] if action == "force_dhw" else b.entities["holiday"]
                    desired = "off" if action == "holiday_off" else "on"
                    current = b.ha("/states/"+entity).get("state")
                    if current not in ("on","off"):
                        raise ValueError("device unavailable")
                    if current != desired:
                        b.ha("/services/switch/turn_"+desired, {"entity_id":entity})
                    confirmed = b.ha("/states/"+entity).get("state") == desired
                else:
                    confirmed = True
                with b.lock: b.updated = 0
                result = {"status":0,"confirmed":confirmed}
                b.requests[request_id] = (time.time(),action,200,result)
                logging.info("Nook command: %s; state confirmed=%s",action,confirmed)
                return self.send(200,result)
            except Exception:
                logging.warning("Nook command %s: outcome uncertain; read the current state",action)
                return self.send(502,{"error":"outcome uncertain; check current state"})

    def do_GET(self):
        b = self.server.bridge
        u = urlsplit(self.path)
        if u.path == "/health": return self.send(200, {"status":"ok"})
        if u.path == "/api/display":
            if not (hmac.compare_digest(self.headers.get("access-token", ""), b.options["api_key"])
                    and self.headers.get("ID") == b.options["device_id"]):
                return self.send(401, {"error":"unauthorized"})
            b.last_contact = datetime.now(TZ).isoformat()
            raw_battery = self.headers.get("Percent-Charged", "").strip()
            battery = int(raw_battery) if re.fullmatch(r"[0-9]{1,3}", raw_battery) else None
            if battery is not None and battery > 100: battery = None
            with b.lock:
                if battery != b.nook_battery:
                    b.nook_battery = battery
                    b.updated = 0

            logging.info("Nook contact; battery=%s", re.sub(r"[^0-9]", "", self.headers.get("Percent-Charged", ""))[:3])
            b.refresh()
            expires = int(time.time()) + 7200
            query = urlencode({"rev":b.revision,"expires":expires,"sig":b.signature(b.revision, expires)})
            return self.send(200, {"status":0,"refresh_rate":display_interval(datetime.now(TZ), {"force":"on" if b.force_active else "off", "_fast_poll":time.time()<b.fast_poll_until}),
                "image_url":b.options["public_url"].rstrip("/")+"/screen.png?"+query})
        if u.path == "/screen.png":
            q = parse_qs(u.query)
            rev, exp, sig = [q.get(k,[""])[0] for k in ("rev","expires","sig")]
            try: valid = int(exp) >= time.time() and int(exp) <= time.time()+7500
            except ValueError: valid = False
            if not valid or not hmac.compare_digest(sig, b.signature(rev, exp)):
                return self.send(403, {"error":"expired or invalid image link"})
            if rev != b.revision: return self.send(409, {"error":"refresh display metadata"})
            logging.info("Image downloaded: %s", rev)
            return self.send(200, b.image, "image/png")
        return self.send(404, {"error":"not found"})

def main():
    path = Path(os.environ.get("NOOK_OPTIONS", "/data/options.json"))
    options = json.loads(path.read_text())
    if len(options.get("api_key", "")) < 20:
        raise SystemExit("Set api_key in the app options: at least 20 characters. Do not use an HA token.")
    options["refresh_seconds"] = max(120, min(86400, int(options.get("refresh_seconds",1800))))
    server = ThreadingHTTPServer(("0.0.0.0",8099), Handler)
    server.bridge = Bridge(options)
    logging.info("Nook Casa started on port 8099; hot water and Holiday commands enabled")
    server.serve_forever()

if __name__ == "__main__": main()

