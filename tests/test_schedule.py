from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'nook_casa'))
import server as s
cases = [
 ('2026-11-03T06:00', 3600), ('2026-11-03T06:59', 60),
 ('2026-11-03T07:00', 900), ('2026-11-03T12:00', 900),
 ('2026-11-03T20:15', 900), ('2026-11-03T20:29', 60),
 ('2026-11-03T20:30', 7200), ('2026-11-03T23:30', 7200),
 ('2026-11-04T05:30', 5400), ('2026-10-25T01:30', 7200),
]
for value, expected in cases:
    actual = s.refresh_interval(datetime.fromisoformat(value).replace(tzinfo=s.TZ))
    assert actual == expected, (value, actual, expected)
# The night interval is elapsed seconds even across DST changes.
assert s.refresh_interval(datetime(2026,3,29,1,30,tzinfo=s.TZ)) == 7200
# Configurable mappings are per instance; callers cannot change them via commands.
b = s.Bridge({'entity_soc':'sensor.example_soc','entity_force':'switch.example_dhw','weather_entity':'weather.example','waste_calendar':'calendar.example'})
assert b.entities['soc']=='sensor.example_soc'
assert b.entities['force']=='switch.example_dhw'
assert b.weather=='weather.example' and b.calendar=='calendar.example'
assert s.ENTITIES['force']=='switch.ecodan_heatpump_force_dhw'
print('PASS: day/night boundaries, midnight, DST and instance entity configuration')
