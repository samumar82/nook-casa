# Configuration and data

Public server versions 0.3.0 and later expose entity IDs as app options, so you do not need to edit Python. Defaults are examples; your home's entities are not discovered automatically.

| Option | Data | Expected unit |
| --- | --- | --- |
| `entity_soc` | Home battery state of charge | % |
| `entity_solar` | Cumulative solar generation today | kWh |
| `entity_grid` | Grid energy imported today | kWh |
| `entity_consumption` | Total home energy consumption today | kWh |
| `entity_spanky` | EV battery charge, displayed as XPENG | % |
| `entity_acs` | Current domestic hot water temperature | °C |
| `entity_force` | Switch that starts forced hot water heating | on/off |
| `entity_holiday` | Holiday Mode switch | on/off |
| `entity_operation` | Heat pump operating state | text |
| `entity_aqi` | Air quality index | numeric index |
| `weather_entity` | Weather entity supporting daily forecasts | weather |
| `waste_calendar` | Waste collection calendar | calendar |

`entity_spanky` and `entity_acs` are retained internal option names for compatibility. The visible labels are **XPENG** and **HOT WATER**. Entity IDs, API action names and the app package are identifiers, not interface translations; existing configured IDs remain unchanged.

There is no automatic Wh-to-kWh conversion. Choose daily energy counters already expressed in kWh. Instantaneous power in W is not interchangeable with daily energy in kWh. AQI is shown numerically without assigning an arbitrary qualitative scale.

The hot water and Holiday Mode commands are designed for switches with semantics equivalent to Ecodan Force DHW and Holiday Mode. Check their meaning before mapping different entities. Only the two configured switches accept commands, and the client asks for confirmation. Commands are rejected if the known state is neither on nor off.

## Refresh schedule

The server returns `refresh_rate` as follows:

- 07:00 ≤ local time < 20:30: 900 seconds.
- Otherwise: 7200 seconds.
- When the next time-window boundary is closer, use the remaining time to that boundary.

Intervals start at the latest contact; they are not necessarily aligned to quarter-hour clock times. Wake-up and Wi-Fi reconnection may add delay. The time zone is `Europe/Rome`, including daylight saving time. The legacy `refresh_seconds` option remains for compatibility but does not override this schedule.

## Saints and holidays

Major Italian holidays are defined locally and displayed with English names. On other days the server tries to read an English saint name from Vatican News and caches the result in `/data/saint_cache_en.json`. If it cannot retrieve a name, it leaves the field empty. This may make one daily HTTPS request to Vatican News; no home states or API keys are sent.

The interface is English; the schedule and holiday calendar retain their original Italian regional settings. Home Assistant entity state strings and calendar event titles are displayed as provided by their source and are not automatically translated.

## Calendar

The server searches the next 30 days, including today, and groups event titles on the first available collection date. Results depend on the source integration's event contents and timing.

## Limitations

The page is an image, not a Lovelace dashboard; it does not execute JavaScript on the Nook. Missing data appears as `--` or an unavailable message. Manual refresh invalidates the renderer cache but does not force HA integrations to fetch new upstream data. Command confirmation uses an immediate state read; integrations that update more slowly may yield an uncertain result even when the command arrived.
