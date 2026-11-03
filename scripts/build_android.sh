#!/usr/bin/env bash
# Legacy Android build. Toolchain locations must be supplied by the developer.
set -euo pipefail
: "${ANDROID_PLATFORM_JAR:?Set path to android-20/android.jar}"
: "${ANDROID_BUILD_TOOLS:?Set directory containing aapt, dx, zipalign, apksigner}"
: "${ECJ_JAR:?Set path to Eclipse ECJ 3.33 jar}"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root/android"
mkdir -p gen bin/classes
for dependency in core prov bctls-jdk15on; do
    test -f "libs/spongycastle-$dependency-1.58.0.0.jar" || {
        echo "Missing SpongyCastle dependency; see android/libs/README_SPONGYCASTLE.md" >&2
        exit 1
    }
done
"$ANDROID_BUILD_TOOLS/aapt" package -f -m -J gen -M AndroidManifest.xml -S res -I "$ANDROID_PLATFORM_JAR" -F bin/resources.ap_
find src gen -name '*.java' | sort > bin/sources.txt
java -jar "$ECJ_JAR" -source 1.6 -target 1.6 -bootclasspath "$ANDROID_PLATFORM_JAR" \
    -classpath 'libs/spongycastle-core-1.58.0.0.jar:libs/spongycastle-prov-1.58.0.0.jar:libs/spongycastle-bctls-jdk15on-1.58.0.0.jar' \
    -d bin/classes @bin/sources.txt
"$ANDROID_BUILD_TOOLS/dx" --dex --min-sdk-version=7 --output=bin/classes.dex bin/classes libs/*.jar
cp bin/resources.ap_ bin/nook-casa-unsigned.apk
(cd bin && zip -q nook-casa-unsigned.apk classes.dex)
"$ANDROID_BUILD_TOOLS/zipalign" -f 4 bin/nook-casa-unsigned.apk bin/nook-casa-aligned.apk
printf '%s\n' 'Unsigned aligned APK: android/bin/nook-casa-aligned.apk' 'Sign with your own private key and v1 JAR signature before installing.'
