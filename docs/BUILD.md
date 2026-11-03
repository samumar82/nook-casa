# Building from source

## Server

The app uses `python:3.12-slim-bookworm`, Pillow 11.3.0, DejaVu fonts and tzdata. Home Assistant Supervisor builds the Dockerfile. No server modules are compiled or installed on the Nook.

For development outside Supervisor, set `NOOK_OPTIONS` to a JSON options file, `NOOK_HA_API` to `http://HOST:8123/api`, and `SUPERVISOR_TOKEN` to a valid HA token in your local environment only. Do not commit the token or include it in logs. In app/add-on mode, Supervisor supplies its token automatically.

## Legacy Android client

Runtime API 7, Java 6 source/bytecode, legacy DEX and **v1** JAR signing. The verified toolchain is:

- OpenJDK 17 to run ECJ, dx and apksigner;
- Eclipse ECJ 3.33;
- Android platform **android-20** (`android.jar`);
- Android Build Tools **28.0.3**: aapt, dx, zipalign and apksigner;
- SpongyCastle `core`, `prov` and `bctls-jdk15on`, version **1.58.0.0**.

Compile platform 20 does not change the minimum runtime API 7. Avoid newer Java/Android APIs that do not exist on the device. Sources retain the historical path `src/com/bpmct/trmnl_nook_simple_touch`, while their declared package is `it.samuele.nookcasa`.

Download dependencies as explained in [README_SPONGYCASTLE.md](../android/libs/README_SPONGYCASTLE.md), then run from the repository root:

```bash
export ANDROID_PLATFORM_JAR=/path/to/android-20/android.jar
export ANDROID_BUILD_TOOLS=/path/to/build-tools/28.0.3
export ECJ_JAR=/path/to/ecj.jar
bash scripts/build_android.sh
```

The output is `android/bin/nook-casa-aligned.apk`, which is **not yet signed**. To install your own build, generate and keep your own private key, then sign using apksigner:

```bash
"$ANDROID_BUILD_TOOLS/apksigner" sign \
  --ks /private/path/key.p12 --ks-key-alias your-alias \
  --min-sdk-version 7 --v1-signing-enabled true --v2-signing-enabled false \
  --out android/bin/nook-casa-custom.apk android/bin/nook-casa-aligned.apk
"$ANDROID_BUILD_TOOLS/apksigner" verify --min-sdk-version 7 android/bin/nook-casa-custom.apk
```

Let apksigner prompt for the password; do not put it in the command or repository. The private key for the distributed APK is not included. v1 signing is essential for Android 2.1. Keep the same key for subsequent updates, otherwise Android rejects `install -r`.

## Constraints to preserve

The renderer and client share the button coordinates documented in [MOCKUP.md](MOCKUP.md). The inherited rotation handling is required by Nook firmware; do not change framebuffer behavior blindly. The screensaver is written before sleep, and the sleep cycle derives from upstream.

The client also retains inherited TRMNL screens and features. Nook Casa's supported workflow is the local server with manually entered credentials; showcase and cloud registration are unnecessary and unverified here.
