# Configurazione e dati

Le opzioni del server pubblico 0.3.0 permettono di scegliere le entità senza modificare Python. I valori predefiniti sono esempi: non vengono scoperte automaticamente le entità della tua casa.

| Opzione | Contenuto | Unità attesa |
| --- | --- | --- |
| `entity_soc` | Stato carica batteria di casa | % |
| `entity_solar` | Produzione solare cumulata oggi | kWh |
| `entity_grid` | Energia importata dalla rete oggi | kWh |
| `entity_consumption` | Consumo totale casa oggi | kWh |
| `entity_spanky` | Batteria auto, visualizzata come XPENG | % |
| `entity_acs` | Temperatura attuale ACS | °C |
| `entity_force` | Switch che avvia la forzatura ACS | on/off |
| `entity_holiday` | Switch Holiday Mode | on/off |
| `entity_operation` | Stato operativo pompa di calore | testo |
| `entity_aqi` | Indice qualità aria | indice numerico |
| `weather_entity` | Entità meteo con previsioni giornaliere | weather |
| `waste_calendar` | Calendario ritiri rifiuti | calendar |

`entity_spanky` è il nome interno legacy dell’opzione; l’etichetta visibile è **XPENG**.

Non viene effettuata conversione Wh→kWh: scegli sensori già in kWh per i tre contatori giornalieri. Potenza istantanea in W e energia giornaliera in kWh non sono intercambiabili. L’AQI viene mostrato come numero senza attribuire arbitrariamente una scala qualitativa.

Le azioni ACS/Holiday sono specifiche di switch con semantica equivalente a Ecodan Force DHW/Holiday. Non collegare queste opzioni a entità con significato diverso senza verificare l’effetto. Il server consente comandi solo sui due switch configurati e il client chiede conferma. Il controllo di disponibilità evita di inviare un comando quando lo stato noto non è on/off.

## Frequenza

Il server risponde con `refresh_rate`:

- 07:00 ≤ ora < 20:30: 900 secondi.
- Altrimenti: 7200 secondi.
- Se il prossimo confine è più vicino, usa il tempo residuo al confine.

Sono intervalli calcolati dall’ultimo contatto, non un allineamento obbligatorio ai quarti d’ora. Risvegli e riconnessione Wi-Fi possono introdurre ritardi. Il fuso è `Europe/Rome` con ora legale. `refresh_seconds` rimane nelle opzioni per compatibilità con le versioni personali, ma non modifica questa pianificazione.

## Santo e festività

Le ricorrenze principali sono definite localmente. Negli altri giorni il server prova a ricavare un nome da Vatican News e lo conserva in `/data/saint_cache.json`. Se la lettura non riesce, non inventa una ricorrenza. Questa funzione può generare una richiesta HTTPS giornaliera verso Vatican News; non invia stati della casa né chiavi.

## Calendario

Il server cerca eventi nei prossimi 30 giorni, includendo il giorno corrente. Raggruppa i nomi degli eventi nella prima data utile. La correttezza dipende dalla qualità e dagli orari degli eventi dell’integrazione calendario.

## Limiti

La pagina è un’immagine: non è una dashboard Lovelace e non esegue JavaScript sul Nook. Dati non disponibili diventano `--` o una descrizione di indisponibilità. Un refresh invalida la cache del renderer, ma non forza l’integrazione HA ad acquisire nuovi dati dalla fonte. Stato ACS/Holiday dopo un comando è verificato con una rilettura immediata; alcune integrazioni aggiornano lo stato più lentamente, quindi l’esito può restare non confermato anche se il comando è arrivato.
