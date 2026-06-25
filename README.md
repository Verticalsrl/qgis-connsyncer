# ConnSyncer

[![License: GPL v2+](https://img.shields.io/badge/License-GPLv2%2B-blue.svg)](LICENSE)
![QGIS](https://img.shields.io/badge/QGIS-3.16%20%E2%80%93%204.x-green.svg)

Plugin QGIS che mostra tutte le sorgenti dati di database (DB) attive nel
progetto corrente e permette di **registrarle nel DB Manager con un solo
click**.

---

## A cosa serve

Quando carichi un layer da un **GeoPackage**, **SpatiaLite** o **PostgreSQL/
PostGIS**, QGIS lo usa come sorgente del layer ma **non aggiunge
automaticamente la connessione al DB Manager**.

Conseguenza: non puoi usare il DB Manager su quella sorgente per creare
tabelle, eseguire query SQL o importare/esportare dati — finché non
ricrei manualmente la connessione, una per una.

**ConnSyncer** elimina questo passaggio: analizza il progetto aperto, elenca
tutte le sorgenti DB trovate e ti permette di salvarle nel DB Manager
scegliendo il nome della connessione.

## Cosa fa, in pratica

- **Scansiona il progetto** e rileva tutti i layer che provengono da un
  database supportato.
- **Elenca le sorgenti** in una tabella con tipo e percorso/host. Le
  connessioni già presenti nel DB Manager sono mostrate in grigio (per non
  sovrascriverle).
- **Permette di rinominare** la connessione (doppio click sul nome) prima del
  salvataggio.
- **Salva con un click** le connessioni selezionate nelle impostazioni di
  QGIS, rendendole subito disponibili nel DB Manager.

### Sorgenti supportate

| Tipo | Note |
|------|------|
| **GeoPackage** (`.gpkg`) | File locali |
| **SpatiaLite** | File SQLite spaziali |
| **PostgreSQL / PostGIS** | Host, porta, database, utente e password presi dalla sorgente del layer |

## Installazione

### Da QGIS (consigliato, una volta pubblicato)
`Plugin → Gestisci e installa plugin…` → cerca **ConnSyncer** → *Installa*.

### Manuale (da questo repository)
1. Scarica/clona il repository.
2. Copia la cartella nel percorso dei plugin QGIS:
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. Riavvia QGIS e abilita **ConnSyncer** in `Plugin → Gestisci e installa plugin`.

## Utilizzo

1. Apri il plugin da **Database → ConnSyncer → DB Connections in Project**
   oppure dal pulsante nella toolbar.
2. La tabella elenca ogni sorgente DB del progetto.
3. (Opzionale) Doppio click sul nome per rinominare la connessione.
4. Seleziona le connessioni desiderate e premi **Save selected**.
5. Riapri il DB Manager per vedere le nuove connessioni.

## Compatibilità

- QGIS **3.16+** (Qt5) e QGIS **4.x** (Qt6).

## Licenza

Distribuito sotto licenza **GNU General Public License v2 o successiva
(GPL-2.0-or-later)**. Vedi il file [LICENSE](LICENSE).

## Autore

**Vertical Srl** — <https://vertical-srl.it> · <info@vertical-srl.it>
