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
    data['nook07_external_error'] = False

    # HA sensors are already scoped to home: do not infer alerts from national DPC counts.
    try:
        all_states = self.ha('/states')
        by_id = {s['entity_id']: s for s in all_states if 'entity_id' in s}
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


