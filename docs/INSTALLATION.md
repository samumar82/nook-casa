# Installazione · Nook Casa 0.10.0

## Hardware

Verificato con **Nook Simple Touch BNRV300**, firmware 1.2.1, Android 2.1 (API 7), root e Wi-Fi. Non usare strumenti di root destinati ad altri modelli. Conservare un backup del Nook.

## Nuova installazione

1. In Home Assistant aggiungi `https://github.com/samumar82/nook-casa` allo store dei repository add-on.
2. Installa **Nook Casa**, apri le opzioni e imposta `public_url`, `device_id`, `api_key` e gli ID delle entità. Usa una chiave casuale non coincidente con il token Home Assistant.
3. Avvia l'add-on e visita `http://IP_HOME_ASSISTANT:8099/health` dalla stessa rete.
4. Prepara il Nook con ADB e installa [l'APK client 0.4.1](../downloads/nook-casa-0.4.1.apk). Il codice Android è disponibile in `android/`.
5. Configura nell'app `http://IP_HOME_ASSISTANT:8099/api`, device ID e chiave locale. Il server fornisce un PNG **600 × 800** contenente la dashboard orizzontale **800 × 600** ruotata.
6. Disponi il Nook fisicamente in orizzontale; la schermata non richiede il touch. Abilita la modalità di sonno/risveglio automatico se già funzionante nel dispositivo.

I valori `entity_*`, `agenda_calendar` e `allergy_risk_entity` devono essere adattati alla propria installazione. Il calendario personale non viene letto se l'entità non è configurata correttamente.

## Aggiornamento locale dalla 0.6.0 personalizzata

La versione 0.10.0 in uso sul dispositivo originale è stata ottenuta da una **0.6.0 locale verificata con SHA-256**, non ricostruendo manualmente il codice. Il suo aggiornamento è stato effettuato dopo un backup di `/addons/nook_casa`. Non applicare una patch vincolata allo SHA di un altro server.

Per normali aggiornamenti del repository la sequenza è:

```bash
ha apps info local_nook_casa
# Dopo aver modificato la versione in config.yaml, ricarica lo store
curl -fsS -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/store/reload
ha apps info local_nook_casa
ha apps update local_nook_casa
ha apps logs local_nook_casa | tail -n 30
```

Questa procedura modifica soltanto l'add-on; eseguire prima il backup e verificare che la versione disponibile sia quella attesa.

## Ripristino

Conservare una copia di `server.py`, `config.yaml` e opzioni add-on precedenti. In caso di errore, ripristinare i file, ricaricare il catalogo locale e aggiornare/ripristinare l'add-on. Non rimuovere l'APK e non cancellare la configurazione del client se il problema riguarda solo il server.

## Sicurezza e diagnostica

La porta 8099 deve restare in rete locale attendibile; l'HTTP legacy non cifra la chiave. Non esporre l'endpoint a Internet. Le immagini sono scaricate tramite URL firmati.

Se la dashboard non appare: controlla `ha apps info local_nook_casa`, i log e la risposta `/health`. Se le scritte sono ruotate male, verifica l'orientamento fisico del Nook. Se appare `— km`, controlla l'unità e il nome del sensore di autonomia.

Vedi anche [Configurazione](CONFIGURATION.md) e [Mockup](MOCKUP.md).
