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
    txt(23,47,data.get('occasion') or '',17,False,740)

    # Top card: next two personal appointments / AQI / local allergens.
    card((12,87,788,164))
    vline(287,95,156,SOFT)
    vline(479,95,156,SOFT)
    agenda=data.get('nook07_agenda') or []
    if agenda:
        for k,item in enumerate(agenda[:2]):
            date=item['start']
            when=('%s %02d'%(short[date.weekday()],date.day))
            if not item.get('all_day'):when+=' '+date.strftime('%H:%M')
            # Keep time/date visible; title is ellipsized only when unavoidable.
            txt(27,100+k*28,when,15,True,108)
            tw=d.textlength(when,font=F(15,True))
            txt(27+tw+8,100+k*28,item['title'],15,False,max(12,247-tw))
    elif data.get('nook07_agenda_error'):
        txt(26,116,'Calendario non disponibile',15,False,252)
    else:
        txt(26,116,'Nessun impegno nei prossimi 7 giorni',14,False,252)

    ic_leaf(302,106,37)
    txt(348,100,'AQI '+fmt(data.get('aqi')),22,True,122)
    try:
        aqi=float(data.get('aqi'))
        aqi_label='Buona' if 0<=aqi<=50 else 'Moderata' if aqi<=100 else 'Elevata'
    except (ValueError,TypeError):aqi_label='Non disponibile'
    txt(348,132,aqi_label,13,False,120)
    ic_flower(498,107,37)
    pollen=data.get('nook07_allergens') or '—'
    txt(544,100,'Allergeni: '+str(pollen).capitalize(),18,True,230)
    txt(544,132,data.get('nook10_allergen_place') or 'Casa',13,False,230)

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
    ic_battery(185,274,46,28,data.get('soc'))
    txt(248,259,'Batteria casa',14,False,155)
    txt(248,282,fmt(data.get('soc'))+'%',26,True,155)
    ic_car(428,272,54,34)
    txt(495,259,'XPENG',14,False,149)
    txt(495,281,fmt(data.get('spanky'))+'%',26,True,146)
    range_km=data.get('nook09_ev_range')
    txt(495,306,(fmt(range_km)+' km' if valid(range_km) else '— km'),14,False,144)

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
    txt(674,227,'Prossimo ritiro',12,False,103)
    raw=str(data.get('waste_name') or 'Non disponibile')
    pieces=raw.split()
    name_lines=[];cur=''
    for word in pieces:
        test=(cur+' '+word).strip()
        if d.textlength(test,font=F(16,True)) <= 101:cur=test
        else:
            if cur:name_lines.append(cur)
            cur=word
    if cur:name_lines.append(cur)
    for j,part in enumerate(name_lines[:2]):txt(674,244+j*20,part,16,True,101)
    waste_date=str(data.get('waste_date') or '—')
    for full,abbr in (('lunedì','Lun'),('martedì','Mar'),('mercoledì','Mer'),('giovedì','Gio'),('venerdì','Ven'),('sabato','Sab'),('domenica','Dom')):
        if waste_date.lower().startswith(full):
            waste_date=abbr+waste_date[len(full):]
            break
    for full,abbr in (('gennaio','gen'),('febbraio','feb'),('marzo','mar'),('aprile','apr'),('maggio','mag'),('giugno','giu'),('luglio','lug'),('agosto','ago'),('settembre','set'),('ottobre','ott'),('novembre','nov'),('dicembre','dic')):
        waste_date=waste_date.replace(full,abbr)
    txt(674,295,waste_date,13,True,101)

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
        face=F(17,False); available=708
        if d.textlength(remaining,font=face)<=available:
            portion=remaining; remaining=''
        else:
            words=remaining.split()
            selected=[]
            for word in words:
                candidate=' '.join(selected+[word])
                if d.textlength(candidate,font=face)<=available:selected.append(word)
                else:break
            portion=' '.join(selected) if selected else fit(remaining,16,available)
            remaining=remaining[len(portion):].lstrip()
        if i == news_lines_needed-1 and remaining:
            portion=fit(portion.rstrip('…')+'…',17,available)
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
