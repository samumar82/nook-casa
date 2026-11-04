# Installation

## 1. Prepare the Nook

This guide assumes a **rooted Nook Simple Touch BNRV300**. The original setup used NookManager, with a complete backup made before system changes. Do not use rooting images intended for other models. Keep a copy of the backup outside the microSD card.

Enable ADB using a tool available on your rooted device. For Wi-Fi ADB, the PC and Nook must be able to reach each other. Never expose port 5555 to the Internet. Root is used for device preparation; individual hot water commands do not require root.

## 2. Install the Home Assistant app

Open **Settings → Apps / Add-ons → Store → menu → Repositories** and add:

```text
https://github.com/samumar82/nook-casa
```

Reload the store, open **Nook Casa** and install it. The app is built locally, so the initial installation may take several minutes. The Dockerfile's package repositories must be reachable.

### Alternative: local installation

In the HA Terminal with access to `/addons`, run a downloaded copy of `scripts/install_local.sh`, or copy this repository's `nook_casa` directory into `/addons/nook_casa`. The script refuses to overwrite an existing directory and generates a local key.

```bash
bash /config/install_local.sh
ha apps install local_nook_casa
```

If the store does not show the app immediately, the CLI can install the local slug directly. `ha store reload` may take time when other repositories are slow. Restarting the host is normally unnecessary.

## 3. Configure the server

Generate a local key in the HA Terminal:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'
```

Set these app options:

- `public_url`: `http://HOME_ASSISTANT_IP:8099`, without `/api`.
- `device_id`: for example, `nook-casa`.
- `api_key`: the generated key, at least 20 characters long.
- Entities: replace the examples with your entity IDs; see [CONFIGURATION.md](CONFIGURATION.md).

Do not share screenshots containing the key. Start the app and check it from a computer on the LAN:

```bash
curl --max-time 15 http://HOME_ASSISTANT_IP:8099/health
```

Expected response: `{"status":"ok"}`. The port may take a few seconds to become available after startup. For local installations:

```bash
ha apps start local_nook_casa
ha apps logs local_nook_casa
```

For repository-store installations, Supervisor assigns a repository-specific slug prefix. Use the UI or find the correct slug with `ha apps list`.

## 4. Install the client from Windows

Download the APK from `downloads/` and the official [Google Platform Tools](https://developer.android.com/tools/releases/platform-tools). Open PowerShell in the directory containing `adb.exe`.

On the Nook, **choose Exit in the original TRMNL app**. Do not keep both clients running: they share a screensaver path and may have competing timers.

Replace the Nook IP and APK path:

```powershell
.\adb.exe connect NOOK_IP:5555
.\adb.exe -s NOOK_IP:5555 install -r "C:\path\nook-casa-0.4.1.apk"
.\adb.exe -s NOOK_IP:5555 shell am start -n it.samuele.nookcasa/.DisplayActivity
```

The package is `it.samuele.nookcasa`, separate from the original `com.bpmct.trmnl_nook_simple_touch`. It does not automatically inherit the original app's credentials.

## 5. Configure the client

Open **Settings → Edit Credentials**:

| Field | Value |
| --- | --- |
| API Base URL | `http://HOME_ASSISTANT_IP:8099/api` |
| Device ID | The server's `device_id` |
| API Key | The local key, not a Home Assistant token |

Save the settings. Enable **Allow HTTP** in the client's network settings if needed. Enable **Sleep between updates** for battery operation. In the original Nook settings, select the **TRMNL** screensaver with a 2-minute timeout, as suggested by the client. The image is saved to `/media/screensavers/TRMNL/display.png`.

Wake the device before using touch controls and allow Wi-Fi to reconnect if necessary. REFRESH reloads the page; HEAT WATER and CHANGE open confirmation controls. Tapping outside these three regions opens the menu.

## Updates and rollback

For store installations, update the app through the UI and review its options. Update the client only when a new APK is released; server and client versions are independent.

For local installations, back up `/addons/nook_casa` and the app options before replacing source files, then use `ha apps update local_nook_casa` and start the app when its version changes. Use rebuild only when the source changes without a version change. Older personal self-extracting update scripts are not this public repository's update channel.

The included APK is signed. Updates for the same package must use the same signing key. A build signed with your own key may require uninstalling the distributed APK first, which removes its local preferences. The maintainer's private signing key is not published.

To return to the original client, choose **Exit** in Nook Casa and open TRMNL. Restore the previous server source and matching options from your backup if needed. Never restore another Nook's full-device backup onto your device.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `adb.exe` is not recognized | Open PowerShell in Platform Tools or use the executable's full path |
| ADB is offline or connection is refused | Wake the Nook; check Wi-Fi and TCP ADB |
| Tapping a button opens TRMNL | The original client is still running, or the new client has not been launched |
| TLS error against an HTTP port | Use `http://`, not `https://`, and enable HTTP in the client |
| A value shows `--` | Check entity IDs, availability, HA access and server logs |
| Empty weather forecast | The weather entity must support `weather.get_forecasts` with type `daily` |
| Clock appears frozen | It is printed in the PNG and only changes at refresh; the time zone is Europe/Rome |
| Command outcome is uncertain | Check the switch in HA and refresh the page before trying again |
| Black bars instead of the page | Check the Nook Casa client, PNG and screensaver; preserve logs and version information before changing framebuffer behavior |

## Upgrading to layout 0.4.0

Update both the server and APK to 0.4.0 for touch feedback. The package and signing key are unchanged, so `adb install -r` preserves client preferences. Active forced hot water heating is checked every 60 seconds; this uses more battery during a cycle. The switch controls the visual active state; the app does not change the heating setpoint or terminate the cycle itself.

Layout 0.4.1 also requires client 0.4.1: the hot water button is narrower and its touch region has moved to match the visible frame.
