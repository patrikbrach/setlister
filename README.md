# Setlist Lookup

Lokalt webbverktyg för att slå upp setlister via [setlist.fm API](https://api.setlist.fm/docs/1.0/index.html).

## Kom igång

```bash
# Installera beroenden
pip install -r requirements.txt

# Starta appen (öppnar automatiskt http://localhost:8000 i webbläsaren)
python main.py
```

## Användning

1. Klistra in din setlist.fm API-nyckel i fältet högst upp
   - Skaffa gratis på [setlist.fm/settings/api](https://www.setlist.fm/settings/api)
2. Ladda upp en Excel-fil (.xlsx) med kolumnerna:

| Kolumn | Obligatorisk | Exempel |
|---|---|---|
| Artist | ✅ | Radiohead |
| Datum / Date | ✅ | 2023-06-15 |
| Venue / Plats / Lokal | ❌ | Annexet |

**Datumformat som accepteras:** `2024-06-15`, `15-06-2024`, `15/06/2024`, `15.06.2024`

3. Klicka **Hämta setlister** – resultaten strömmar in rad för rad
4. Klicka på en rad för att expandera låtlistan
5. Klicka **Exportera till Excel** för en sammanfattningsfil

## Projektstruktur

```
setlist-lookup/
├── main.py              # FastAPI-app + endpoints
├── setlist_client.py    # Logik för setlist.fm API-anrop
├── excel_reader.py      # Excel-parsning med pandas
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
└── README.md
```
