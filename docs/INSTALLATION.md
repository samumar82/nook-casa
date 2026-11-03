# Installazione

## 1. Preparare il Nook

Questa guida parte da un **Nook Simple Touch BNRV300 già con root**. Nell’installazione originale è stato usato NookManager, con backup completo prima delle modifiche. Non usare immagini di root di altri modelli. Conserva una copia del backup fuori dalla microSD.

Abilita ADB sul Nook con lo strumento disponibile sul tuo sistema rooted. Se usi ADB via Wi-Fi, PC e Nook devono potersi raggiungere. La porta 5555 non deve essere esposta a Internet. Il root non serve ai singoli comandi ACS: serve alla preparazione/installazione del vecchio dispositivo.

## 2. Installare l’app Home Assistant

In **Impostazioni → App / Componenti aggiuntivi → Store → menu → Repository**, aggiungi:

```text
https://github.com/samumar82/nook-casa
```

Ricarica lo Store, apri **Nook Casa** e installa. L’app viene compilata localmente: il primo avvio richiede alcuni minuti. Deve essere disponibile l’accesso ai repository dei pacchetti del Dockerfile.

### Alternativa: installazione locale

Dal Terminale HA con accesso a `/addons`, scarica ed esegui `scripts/install_local.sh` oppure copia la cartella `nook_casa` della repository in `/addons/nook_casa`. Lo script rifiuta di sovrascrivere una cartella esistente e genera una chiave locale.

```bash
bash /config/install_local.sh
ha apps install local_nook_casa
```

Se lo Store non mostra subito l’app, la CLI può installare direttamente lo slug locale. `ha store reload` può impiegare tempo se altre repository sono lente. Non è normalmente necessario riavviare l’intero host.

## 3. Configurare il server

Genera una chiave nel terminale HA:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'
```

Nelle opzioni dell’app inserisci:

- `public_url`: `http://IP_DI_HOME_ASSISTANT:8099`, senza `/api`.
- `device_id`: ad esempio `nook-casa`.
- `api_key`: la chiave appena generata, almeno 20 caratteri.
- Entità: sostituisci gli esempi con le tue, come spiegato in [CONFIGURATION.md](CONFIGURATION.md).

Non condividere screenshot con la chiave. Avvia l’app; verifica da un computer della LAN:

```bash
curl --max-time 15 http://IP_DI_HOME_ASSISTANT:8099/health
```

Risultato atteso: `{"status":"ok"}`. Subito dopo lo start può servire qualche secondo prima che la porta risponda. Per installazioni locali:

```bash
ha apps start local_nook_casa
ha apps logs local_nook_casa
```

Con installazione da repository lo slug include il prefisso assegnato dal Supervisor: usa la UI oppure individua quello corretto con `ha apps list`.

## 4. Installare il client da Windows

Scarica l’APK in `downloads/` e i [Platform Tools ufficiali Google](https://developer.android.com/tools/releases/platform-tools). Apri PowerShell nella cartella che contiene `adb.exe`.

Sul Nook, **esci dal vecchio TRMNL con Exit**. Non tenere attivi entrambi i client: condividono il percorso del salvaschermo e possono avere timer concorrenti.

Sostituisci IP e percorso APK:

```powershell
.\adb.exe connect IP_DEL_NOOK:5555
.\adb.exe -s IP_DEL_NOOK:5555 install -r "C:\percorso\nook-casa-0.2.1.apk"
.\adb.exe -s IP_DEL_NOOK:5555 shell am start -n it.samuele.nookcasa/.DisplayActivity
```

L’app ha package `it.samuele.nookcasa`, separato dall’originale `com.bpmct.trmnl_nook_simple_touch`. Non eredita automaticamente le sue credenziali.

## 5. Configurare il client

Apri **Settings → Edit Credentials**:

| Campo | Valore |
| --- | --- |
| API Base URL | `http://IP_DI_HOME_ASSISTANT:8099/api` |
| Device ID | Lo stesso `device_id` del server |
| API Key | La chiave locale, non un token HA |

Salva. Abilita **Allow HTTP** nelle impostazioni di rete del client, se necessario. Attiva **Sleep between updates** per la batteria. Nelle impostazioni originali Nook seleziona il salvaschermo **TRMNL** con timeout di 2 minuti, come suggerito dal client. Viene usato `/media/screensavers/TRMNL/display.png`.

Risveglia il dispositivo per usare i pulsanti; attendi l’eventuale riconnessione Wi-Fi. AGGIORNA ricarica la pagina; SCALDA ACS e CAMBIA mostrano le conferme. Fuori dalle tre zone compare il menu.

## Aggiornare e tornare indietro

Per installazioni da Store, aggiorna l’app dalla UI e ricontrolla le opzioni. Il client cambia solo quando viene pubblicato un nuovo APK: server e client hanno versioni indipendenti.

Per installazioni locali, conserva un backup di `/addons/nook_casa` e delle opzioni prima di sostituire i sorgenti, poi stop/rebuild/start dello slug locale. I vecchi script personali autoestraenti non sono il canale di aggiornamento di questa repository pubblica.

L’APK qui incluso è firmato. Aggiornamenti dello stesso package devono avere la stessa firma. Una compilazione firmata con una propria chiave richiede la rimozione dell’APK precedente se le firme differiscono, con perdita delle preferenze locali. La chiave privata del manutentore non è pubblicata.

Per tornare al client originale: menu **Exit** in Nook Casa e avvio di TRMNL. Per ripristinare anche il server usa il backup della versione precedente, mantenendo le relative opzioni. Non ripristinare mai un backup completo del Nook di un altro dispositivo.

## Problemi comuni

| Sintomo | Verifica |
| --- | --- |
| `adb.exe` non riconosciuto | Apri PowerShell nella cartella Platform Tools oppure usa il percorso completo |
| ADB offline/rifiutato | Risveglia il Nook; controlla Wi-Fi e ADB su TCP |
| Toccare un pulsante apre TRMNL | È ancora attivo il client originale, oppure il nuovo client non è quello avviato |
| Errore TLS su porta HTTP | L’URL deve iniziare con `http://`, non `https://`; abilita HTTP nel client |
| Valore `--` | Entità errata/non disponibile o lettura HA fallita; controlla opzioni e log |
| Meteo vuoto | L’entità deve supportare `weather.get_forecasts`, tipo `daily` |
| Orario fermo | È stampato nel PNG e cambia a ogni aggiornamento; il fuso è Europe/Rome |
| Comando dall’esito incerto | Controlla lo switch in HA e aggiorna la pagina prima di riprovare |
| Barre nere invece della pagina | Verifica client Nook Casa, PNG corretto e salvaschermo; conserva log e versione prima di modificare il framebuffer |
