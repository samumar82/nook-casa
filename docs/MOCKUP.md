# Il giornale di casa: anteprima

![Mockup 600 × 800 con dati dimostrativi](images/mockup.png)

La pagina è prodotta dallo stesso renderer Pillow utilizzato dal server. L’anteprima contiene dati di esempio, non letture di una casa reale.

La sezione Energia contiene cinque colonne: batteria casa, solare oggi, rete oggi, consumo casa oggi e XPENG. I pulsanti SCALDA ACS, CAMBIA e AGGIORNA sono riquadrati e centrati rispetto alle rispettive righe.

## Aree touch del client 0.2.1

Coordinate nel PNG di riferimento 600 × 800, riscalate dal client alla vista:

| Pulsante | X | Y | Azione |
| --- | --- | --- | --- |
| SCALDA ACS | 318–576 | 477–528 | Conferma avvio riscaldamento ACS |
| CAMBIA | 438–576 | 569–603 | Scelta Attiva / Disattiva Holiday |
| AGGIORNA | 438–576 | 738–770 | Rilettura dati e nuovo PNG |

Queste coordinate fanno parte dell’interfaccia tra server e APK: spostare i pulsanti nel renderer richiede aggiornare anche il client. Il resto della superficie apre il menu. In standby il touch non è attivo.

Rigenera l’anteprima dalla radice della repository:

```bash
python3 tests/test_server.py
```
