# 0.4.3 — 2026-11-04

- Increase the saint header to 30 px and use the full available row.
- Remove the header clock; retain footer update times and Nook battery.
- Remove the divider between operation state and Holiday Mode; align both labels at x=24.
- Match Holiday artwork to the existing client hitbox (438,569)-(576,603); keep vertical text centering.
- Verify all three buttons against Android touch and pressed-feedback bounds. Client 0.4.1 remains compatible.
- Refresh renderer previews and document these changes.

# Changelog

## Server and client 0.4.1

- Center the Holiday Mode label and state within their columns.
- Slightly enlarge the saint line.
- Narrow the hot water button and move its touch and feedback region to match.

## Server and client 0.4.0

- Replace the newspaper title with a larger bold date, saint and time header.
- Render monochrome weather icons and waste material symbols without external assets.
- Remove the waste heading and shorten collection dates.
- Show immediate black touch feedback and retain a black hot water button while its switch is active.
- Remove the separate override label; poll the active cycle every 60 seconds.
- Preserve button coordinates, package and signing key.

## Server 0.3.2

- Show the Nook battery percentage in the top-right corner of the first line.
- Read the existing client battery header; no APK update required.
- Refresh the cached image when the reported percentage changes; display `--` if unavailable.

## Server 0.3.1 / client 0.2.2 — English edition

- Translate all project documentation, app metadata and installation messages into English.
- Translate dashboard headings, dates, weather descriptions, buttons, states and server logs.
- Use English daily saint names and English names for the existing Italian holiday calendar.
- Translate hot water/Holiday confirmations and command outcome messages in the Android client.
- Regenerate the mockup and publish a newly signed English APK with updated checksum.
- Retain entity option names, API actions, package and touch coordinates for compatibility.

## Server 0.3.0 — first public edition

- Configurable entity IDs in Home Assistant app options, with example defaults.
- Installation guide, data mapping, verified hardware and renderer preview.
- Client source and APK 0.2.1 with attribution and license notices.

## Server 0.2.2 — personal edition

- Refresh every 15 minutes between 07:00 and 20:30, otherwise every 2 hours.
- Add total home energy consumption today alongside home battery, solar, grid and EV data.

## Server / client 0.2.1

- Align buttons and status labels; use a clearer hot water heating label.
- Separate `it.samuele.nookcasa` client with confirmed hot water/Holiday controls and manual refresh.

## Server 0.1.x

- Initial local HA → PNG → Nook client bridge, originally read-only.

