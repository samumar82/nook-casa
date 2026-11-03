#!/usr/bin/env bash
set -euo pipefail
# Run a downloaded copy in the Home Assistant Terminal, with /addons exposed.
python3 - <<'PY'
from pathlib import Path
import io, json, secrets, tarfile
from urllib.request import urlopen
root = Path('/addons')
target = root/'nook_casa'
if not root.is_dir():
    raise SystemExit('/addons non disponibile: usare il Terminale Home Assistant.')
if target.exists():
    raise SystemExit('/addons/nook_casa esiste già: nessun file sovrascritto.')
url = 'https://api.github.com/repos/samumar82/nook-casa/tarball/main'
with urlopen(url, timeout=60) as response:
    archive = response.read(20000000)
with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
    files = []
    for member in tar.getmembers():
        parts = Path(member.name).parts
        if len(parts) != 3 or parts[1] != 'nook_casa' or not member.isfile():
            continue
        files.append((parts[-1], tar.extractfile(member).read()))
    if not any(name == 'config.yaml' for name, data in files):
        raise SystemExit('Archivio non valido: config.yaml mancante.')
    target.mkdir()
    for name, data in files:
        (target/name).write_bytes(data)
key = secrets.token_urlsafe(24)
p = target/'config.yaml'
p.write_text(p.read_text().replace('api_key: ""', 'api_key: '+json.dumps(key)))
print('Sorgenti preparati: /addons/nook_casa')
print('API Key locale (non condividere): '+key)
print('Installa con: ha apps install local_nook_casa')
print('Configura public_url ed entità nelle opzioni prima di avviare.')
PY
