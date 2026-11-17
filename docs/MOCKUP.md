# Mockup definitivo: Nook Casa 0.10.0 orizzontale

![Nook Casa 0.10.0 · 800×600](images/mockup-landscape-v010.png)

Questa immagine è stata generata dal **renderer Python/Pillow effettivo**, con dati dimostrativi. La pagina logica misura 800 × 600 pixel; il server ruota il PNG a 600 × 800 prima di inviarlo al client Android esistente.

## Disposizione della pagina

- **Testata:** data, santo del giorno e `LDP` in alto a destra.
- **Fascia alta:** prossimi due impegni di calendario, AQI, allergeni.
- **Corpo:** quattro giorni meteo; FV, consumi e rete; batteria casa e XPENG con km residui; PDC, ACS, Holiday Mode, ciclo ACS; rifiuti; batteria Nook.
- **Fascia inferiore:** cinque righe di notizie e allerte, **senza titolo né icona d'intestazione**, senza separatore e senza footer. Le icone degli avvisi hanno ciascuna uno spazio dedicato e non si sovrappongono ai testi.

La sezione Protezione Civile usa le allerte delle entità Home Assistant riferite alla zona di casa; lo sciopero prossimo compare solo se attinente e imminente (entro cinque giorni). Informazioni sconosciute mostrano un trattino, mai dati inventati. Le informazioni di Ultimora vengono trattate come notizie, non come allerta ufficiale.

## Posizione fisica e client

Il Nook BNRV300 dispone di uno schermo fisico 600 × 800. Si posiziona **orizzontalmente**, senza necessità di touch; la bitmap fornita all'APK rimane 600 × 800 per compatibilità con il client esistente.

## Versioni precedenti

I mockup `mockup.png` e `mockup-it.png` illustrano l'interfaccia legacy verticale con pulsanti e sono conservati soltanto per riferimento storico. La schermata corrente approvata è **mockup-landscape-v010.png**.
