# Nuova FLORA UE27

Dashboard interattiva sugli alert dei flussi commerciali UE27, con analisi contestuale della crisi dello Stretto di Hormuz.

## Contenuti

- `dist/index.html`: dashboard statica.
- `dist/data/`: alert, casi Hormuz e serie mensili in JSON.
- `dist/analisi_hormuz_nuova_flora.docx`: documento scaricabile dalla dashboard.
- `build_static_site.py`: generatore a partire dagli output della pipeline nel progetto `terra-package`; richiede pandas e i dati sorgente esterni a questo repository.

I file in `dist` sono già pronti: per visualizzare la dashboard non occorre eseguire la pipeline o interrogare API.

## Avvio locale

```sh
python3 -m http.server 8000 --directory dist
```

Aprire http://localhost:8000. Il server HTTP è necessario per caricare i JSON.

## GitHub Pages

Nelle impostazioni del repository, aprire **Pages** e scegliere **GitHub Actions** come sorgente. Il workflow `pages.yml` pubblica `dist` a ogni push su `main`; può essere avviato anche manualmente dalla scheda Actions.

## Dati e metodologia

Flussi commerciali mensili TERRA/Eurostat COMEXT, da febbraio 2022 a maggio 2026. Per ogni paese UE27 e flusso import/export sono considerati i primi 20 partner e i prodotti CPA a due cifre, esclusa CPA 00. La nota metodologica completa è consultabile nella dashboard. Le segnalazioni Hormuz indicano coerenza temporale ed economica, non causalità.

Sito di origine: https://nuova-flora-ue27.fbrogi.chatgpt.site/
