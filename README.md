# Nook Casa

**Un Nook Simple Touch trasformato in un giornale di casa con Home Assistant.**

Meteo, energia, acqua calda, auto elettrica e prossimo ritiro rifiuti su uno schermo e-ink da 6 pollici. Due pulsanti comandano ACS e Holiday Mode; un terzo aggiorna subito i dati. Il Nook può dormire fra gli aggiornamenti mantenendo visibile la pagina.

<p align="center"><img src="docs/images/mockup.png" width="420" alt="Anteprima dimostrativa del Giornale di casa su schermo 600 × 800" /></p>

*Mockup generato dal renderer reale, con dati dimostrativi. [Apri l’anteprima](docs/MOCKUP.md).* 

## Cosa mostra

- Data estesa e ora italiana, festività principali e santo del giorno quando disponibile.
- Meteo di oggi e dei prossimi tre giorni, temperature minime/massime e indice AQI.
- Batteria di casa, produzione fotovoltaica, prelievo dalla rete e consumo totale di oggi; batteria XPENG.
- Temperatura ACS e stato operativo della pompa di calore; **SCALDA ACS** con conferma.
- Stato Holiday Mode e pulsante **CAMBIA**, con scelte esplicite Attiva/Disattiva.
- Prossimo ritiro rifiuti da un calendario Home Assistant.
- Ora dell’ultimo aggiornamento e della prossima edizione; pulsante **AGGIORNA**.

Intervalli automatici, fuso `Europe/Rome`: **07:00–20:30 ogni 15 minuti**, dalle **20:30 alle 07:00 ogni 2 ore**. Il ritardo si accorcia vicino ai due confini per raggiungerli. Non è un aggiornamento in tempo reale: anche l’orologio stampato nella pagina cambia al refresh.

## Come funziona

Il server Python, eseguito come app/add-on Home Assistant, legge stati, previsioni e calendario e genera un PNG 600 × 800. Il client Android lo scarica via HTTP nella LAN e lo visualizza. Il client conserva il PNG come salvaschermo e programma il risveglio successivo.

I pulsanti sono aree touch nel client sopra l’immagine, non elementi HTML. Fuori dai pulsanti si apre il menu. **In standby occorre prima risvegliare il Nook con un tasto fisico.** La versione TRMNL originale tratta invece i tocchi come apertura del menu: serve l’APK Nook Casa.

## Hardware e compatibilità

| Componente | Requisito / verifica |
| --- | --- |
| E-reader | Barnes & Noble **Nook Simple Touch BNRV300**, senza luce integrata |
| Firmware verificato sul dispositivo | **1.2.1** |
| Sistema | Android **2.1**, API **7** |
| Display | E Ink, 6 pollici, **600 × 800**, ritratto |
| Collegamento | Wi-Fi nella stessa rete raggiungibile da Home Assistant |
| Preparazione | Nook con root; ADB usato per installare il client |
| Server | Home Assistant OS/Supervised con Supervisor e app/add-on |
| Architetture dichiarate dal server | `amd64`, `aarch64` |
| Server verificato nell’installazione originale | HAOS su Proxmox, `amd64` |

Il BNRV300 è il Simple Touch, non il primo Nook del 2009 con secondo schermo LCD. Altri modelli e firmware non sono stati verificati in questo progetto. Non sono richiesti un cloud TRMNL o un suo abbonamento per il percorso locale Nook Casa. Le integrazioni HA di meteo/AQI/auto possono avere proprie dipendenze esterne.

## Installazione rapida

Guida completa: **[INSTALLATION.md](docs/INSTALLATION.md)**.

1. Fai un backup completo del Nook prima di root o modifiche di sistema. Il progetto non automatizza il root.
2. Aggiungi `https://github.com/samumar82/nook-casa` come repository nello Store app/add-on di Home Assistant; installa **Nook Casa**. In alternativa usa l’installazione locale descritta nella guida.
3. Genera una chiave locale, configura `public_url`, `device_id` e le entità nelle opzioni. Avvia l’app e verifica `/health`.
4. Scarica [nook-casa-0.2.1.apk](downloads/nook-casa-0.2.1.apk) e installalo con ADB. Esci da TRMNL originale prima di avviare Nook Casa.
5. Nel client: API Base URL `http://IP_DI_HOME_ASSISTANT:8099/api`, Device ID uguale al server, API Key uguale alla chiave locale.
6. Attiva **Sleep between updates**; nelle impostazioni Nook seleziona il salvaschermo **TRMNL**. Verifica un ciclo completo di standby/risveglio sul dispositivo.

Il server pubblico **0.3.0** aggiunge entità configurabili alle opzioni rispetto alla versione personale 0.2.2. Il client rimane **0.2.1**. [Configurazione e mappa entità](docs/CONFIGURATION.md).

## Sicurezza e comportamento dei comandi

La porta 8099 è destinata alla LAN fidata. L’HTTP è necessario per il percorso legacy qui verificato: chi vede il traffico può leggere la chiave locale. Non esporre questa porta a Internet e non usare il token personale Home Assistant come API Key del Nook. Il server usa internamente `SUPERVISOR_TOKEN`.

`/api/display` e `/api/command` richiedono ID e chiave; le immagini usano URL con firma e scadenza. Il server accetta solo `refresh`, `force_dhw`, `holiday_on`, `holiday_off`. Non accetta nomi di entità o servizi arbitrari dalla richiesta. Le due entità comandabili sono quelle configurate dall’amministratore nelle opzioni.

**Scalda ACS** invia solo `switch.turn_on`: non è un toggle e non spegne un ciclo in corso. Holiday usa ON/OFF espliciti. Gli ID delle richieste evitano duplicazioni durante la finestra di deduplicazione; un esito incerto non produce un retry automatico. Nessuna automazione HA viene modificata. **Aggiorna** legge gli ultimi dati disponibili in HA, senza forzare il polling delle integrazioni.

## Sorgenti e sviluppo

- [`nook_casa/`](nook_casa/): server, Dockerfile e configurazione app Home Assistant.
- [`android/`](android/): sorgente client derivato da TRMNL Nook Simple Touch v0.16.0.
- [`downloads/`](downloads/): APK installabile e checksum.
- [`tests/`](tests/): verifiche con Home Assistant simulato e test delle fasce orarie.
- [`docs/BUILD.md`](docs/BUILD.md): compilazione Android legacy e firma personale.

Esegui i controlli server con Python 3.12, Pillow e tzdata:

```bash
python3 -m pip install -r requirements-dev.txt
python3 tests/test_server.py
python3 tests/test_controls.py
python3 tests/test_schedule.py
```

I test verificano rendering, autenticazione, URL firmati, comandi ammessi, deduplicazione, calendario e intervalli. Il test di rendering rigenera l’immagine dimostrativa. Compilazione DEX e firma dell’APK sono state verificate. Il server locale e il client sono stati provati sul BNRV300; gli ultimi dettagli touch e i risvegli prolungati richiedono ulteriore verifica sul dispositivo. Non è dichiarata un’autonomia in giorni: dipende da batteria, segnale Wi-Fi e frequenza di risveglio.

## Licenza e riconoscimenti

**MIT**, con mantenimento del copyright originale **BPMCT**. Il client deriva da [`usetrmnl/trmnl-nook-simple-touch`](https://github.com/usetrmnl/trmnl-nook-simple-touch), tag `v0.16.0`. Questa è una repository autonoma che unisce client modificato e server HA, non un fork nella rete GitHub del progetto originale. [Provenienza e licenze delle dipendenze](THIRD_PARTY_NOTICES.md).

Progetto indipendente: nessuna affiliazione con Barnes & Noble, TRMNL, Home Assistant, Mitsubishi Electric o XPENG. I marchi appartengono ai rispettivi proprietari.
