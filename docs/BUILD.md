# Compilazione

## Server

L’app utilizza `python:3.12-slim-bookworm`, Pillow 11.3.0, font DejaVu e tzdata. Home Assistant Supervisor costruisce il Dockerfile. Non vengono compilati o caricati moduli sul Nook.

Per sviluppo puoi avviare il server fuori da Supervisor impostando `NOOK_OPTIONS` al percorso di un file JSON di opzioni, `NOOK_HA_API` a `http://HOST:8123/api` e `SUPERVISOR_TOKEN` a un token HA valido nel solo ambiente locale. Non salvare il token nel codice, nei log o nella repository. In modalità add-on il Supervisor fornisce automaticamente il token.

## Client Android legacy

Runtime API 7, sorgente/bytecode Java 6, DEX legacy, firma JAR **v1**. È stato compilato con:

- OpenJDK 17 per eseguire ECJ, dx e apksigner;
- Eclipse ECJ 3.33;
- Android platform **android-20** (`android.jar`);
- Android Build Tools **28.0.3**: aapt, dx, zipalign, apksigner;
- SpongyCastle `core`, `prov`, `bctls-jdk15on`, tutti **1.58.0.0**.

La piattaforma di compilazione 20 non cambia il runtime minimo 7. Evita di introdurre API Java/Android recenti: il dispositivo non le ha. I sorgenti mantengono il percorso storico `src/com/bpmct/trmnl_nook_simple_touch`, ma il package dichiarato è `it.samuele.nookcasa`.

Scarica le dipendenze come descritto in [README_SPONGYCASTLE.md](../android/libs/README_SPONGYCASTLE.md), poi dalla radice della repository:

```bash
export ANDROID_PLATFORM_JAR=/percorso/android-20/android.jar
export ANDROID_BUILD_TOOLS=/percorso/build-tools/28.0.3
export ECJ_JAR=/percorso/ecj.jar
bash scripts/build_android.sh
```

L’output è `android/bin/nook-casa-aligned.apk`, **ancora non firmato**. Per installare un APK creato da te, genera e conserva una tua chiave privata e firma con apksigner:

```bash
"$ANDROID_BUILD_TOOLS/apksigner" sign \
  --ks /percorso/privato/chiave.p12 --ks-key-alias tuo-alias \
  --min-sdk-version 7 --v1-signing-enabled true --v2-signing-enabled false \
  --out android/bin/nook-casa-personale.apk android/bin/nook-casa-aligned.apk
"$ANDROID_BUILD_TOOLS/apksigner" verify --min-sdk-version 7 android/bin/nook-casa-personale.apk
```

Lascia che apksigner chieda la password; non inserirla nel comando o nel repository. La chiave privata usata per l’APK distribuito non è inclusa. La firma v1 è essenziale per Android 2.1. Mantieni la stessa chiave per tutti i tuoi aggiornamenti, altrimenti Android rifiuta `install -r`.

## Vincoli da conservare

Il rendering e il client condividono le coordinate dei pulsanti documentate in [MOCKUP.md](MOCKUP.md). Il sistema di rotazione ereditato dal client originale è necessario sul firmware Nook: non applicare correzioni al framebuffer alla cieca. Il salvaschermo viene aggiornato prima dello standby; il ciclo di sospensione deriva dall’upstream.

Il client conserva anche schermate/funzioni TRMNL ereditate. Il percorso supportato da Nook Casa è quello locale con credenziali inserite manualmente; showcase e registrazione cloud non sono necessari né verificati qui.
