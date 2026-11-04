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
    relative={0: 'Today', 1: 'Tomorrow', 2: 'Day after tomorrow'}
    if delta in relative:return relative[delta]
    return f"{['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day.weekday()]} {day.day} {['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][day.month-1]}"

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
            if re.match(r"^(St[.]? |Saint |Saints |Sts[.]? |Blessed )", label):
                self.labels.append(label[:120])
            self.inside = False

FIXED_OCCASIONS = {
    "01-01":"New Year's Day", "01-06":"Epiphany", "04-25":"Liberation Day (Italy)",
    "05-01":"Labour Day", "06-02":"Republic Day (Italy)",
    "08-15":"Assumption Day", "11-01":"All Saints' Day",
    "12-08":"Immaculate Conception", "12-25":"Christmas Day", "12-26":"St. Stephen's Day",
}

def occasion(now):
    fixed = FIXED_OCCASIONS.get(now.strftime("%m-%d"))
    if fixed: return fixed
    cache = Path(os.environ.get("NOOK_SAINT_CACHE", "/data/saint_cache_en.json"))
    today = now.date().isoformat()
    try:
        saved = json.loads(cache.read_text())
        if saved.get("date") == today: return saved.get("label", "")
    except (OSError, ValueError): pass
    label = ""
    try:
        url = "https://www.vaticannews.va/en/saints/"+now.strftime("%m/%d")+".html"
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

class Bridge:
    def __init__(self, options):
        self.options = options
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

