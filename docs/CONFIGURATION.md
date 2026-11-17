# Configurazione · Nook Casa 0.10.1

Le impostazioni si gestiscono dalle opzioni dell'add-on Home Assistant. I nomi predefiniti sono esempi: sostituiscili con le entità della tua installazione.

| Opzione | Significato | Unità |
| --- | --- | --- |
| `entity_soc` | Stato di carica batteria casa | % |
| `battery_day_charge_entity` | Energia caricata nella batteria **oggi** (predefinito `sensor.batteries_day_charge`) | kWh |
| `battery_day_discharge_entity` | Energia scaricata dalla batteria **oggi** (predefinito `sensor.batteries_day_discharge`) | kWh |
| `entity_solar` | Produzione fotovoltaica odierna | kWh |
| `entity_grid` | Prelievo dalla rete odierno | kWh |
| `entity_consumption` | Consumo energetico domestico odierno | kWh |
| `entity_spanky` | Batteria veicolo, mostrata come XPENG | % |
| `entity_acs` | Temperatura accumulo ACS | °C |
| `entity_force` | Stato comando ciclo forzato ACS, solo informativo sul display | on/off |
| `entity_holiday` | Holiday Mode, solo informativo sul display | on/off |
| `entity_operation` | Stato operazione PDC, es. Space heating | testo |
| `entity_aqi` | Air quality index | numero |
| `weather_entity` | Previsioni giornaliere | weather |
| `waste_calendar` | Calendario prossimi ritiri | calendar |
| `agenda_calendar` | Calendario dei prossimi appuntamenti personali | calendar |
| `allergy_risk_entity` | Livello rischio allergeni (si tenta anche il rilevamento automatico di sensori polleninformation) | testo |
| `ev_range_entity` | Sensore chilometri residui veicolo; facoltativo, rilevato automaticamente se univoco | km |

I due valori della batteria sono **energia giornaliera in kWh**, non potenza istantanea in W e non contatori totali. Se il sensore non è numerico o non ha unità `kWh`, la schermata mostra `—`.

L'autonomia non è derivata dalla percentuale di batteria. Il sistema accetta soltanto sensori numerici in `km` con valore plausibile. Se non ne trova, visualizza `— km`.

## Allerte e scioperi

Per la Protezione Civile sono riconosciute le entità `sensor.dpc_today_alert`, `sensor.dpc_tomorrow_alert` e `sensor.dpc_alert_zone`; i livelli `yellow`, `orange`, `red` generano avvisi. `green` segnala assenza di allerta, mentre `unknown` non viene trasformato in un falso 'tutto bene'.

Per gli scioperi locali, il collector usa `sensor.scioperi_vicini` e in alternativa `sensor.scioperi_prossimo_vicino`, filtrati per eventi nei prossimi cinque giorni. Sono dati forniti dalle integrazioni di Home Assistant, non una verifica diretta dei bollettini ufficiali.

Il titolo di Ultimora deriva da una lettura pubblica del canale Telegram; in caso di rete non disponibile può essere mostrato l'ultimo contenuto con indicazione di dato non aggiornato.

## Batteria Nook

Ricevuta dall'header del client `Percent-Charged`. Non è necessario creare un sensore Home Assistant. La percentuale cambia quando il lettore contatta il server.

## Aggiornamento orario

Europe/Rome: 15 minuti durante il giorno (07:00–20:30), 2 ore di notte. Un ciclo ACS attivo può ridurre temporaneamente l'intervallo di polling per preservare il comportamento esistente.

## Privacy e sicurezza

Non salvare l'API key nelle screenshot o nei file pubblici. Usare la porta 8099 solo in LAN fidata. I nomi dei calendari e delle entità locali non vanno incorporati in screenshot con appuntamenti privati.

La modalità 0.10.0 è **sola visualizzazione**: non sono disegnati pulsanti touch. La compatibilità server può mantenere endpoint di comando legacy, già protetti da autenticazione; per eliminarli occorre una modifica API separata.
