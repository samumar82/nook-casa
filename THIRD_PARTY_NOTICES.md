# Provenienza e componenti di terze parti

## Client TRMNL Nook Simple Touch

Origine: https://github.com/usetrmnl/trmnl-nook-simple-touch

Base: tag **v0.16.0**, licenza **MIT**, copyright **2026 BPMCT**. Il testo originale completo è conservato in `android/LICENSE`; il file `LICENSE` della repository mantiene lo stesso avviso e aggiunge l’attribuzione alle modifiche Nook Casa.

Modifiche Nook Casa: package/app separati, aree touch sul PNG, conferme ACS/Holiday, invio di comandi locali autenticati con ID richiesta, gestione della riconnessione Wi-Fi prima dei comandi. Gestione e-ink, salvaschermo, rotazione, TLS legacy, impostazioni e ciclo sleep derivano dal progetto originale. Le risorse Android sono conservate dalla distribuzione upstream.

## SpongyCastle / Bouncy Castle

Il client e l’APK includono SpongyCastle **1.58.0.0**, componenti `core`, `prov`, `bctls-jdk15on`. Sorgente: https://github.com/rtyley/spongycastle . Licenza: https://github.com/rtyley/spongycastle/blob/spongy-master/LICENSE.html .

Copyright (c) 2000-2017 The Legion of the Bouncy Castle Inc. (http://www.bouncycastle.org)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Server e dipendenze runtime

Server Nook Casa: MIT, copyright 2026 Samuele Marchetti. Python/Pillow, Debian, DejaVu e tzdata sono dipendenze ottenute durante la costruzione dell’immagine, con le rispettive licenze; non sono riclassificate come MIT di questo progetto. Pillow: https://github.com/python-pillow/Pillow/blob/main/LICENSE .

## Dati e marchi

Le letture HA e le previsioni dipendono dalle integrazioni configurate dall’utente. Il nome del santo può essere ricavato dalla pagina giornaliera Vatican News, con cache locale; non si redistribuiscono articoli o immagini del sito. Nessuna licenza software conferisce diritti sui marchi dei prodotti citati.
