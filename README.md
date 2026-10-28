# aragon-backend-
Aragon Ultima FastAPI Backend 
# ARAGON ULTIMA :: HARD ROOT v26.0 (FastAPI Backend)

**Status:** Standards-Native / QES-Validated / Audit-Ready
**Doktrin:** "Rauschfrei. Signiert. Unbestechlich."

Dieses Repository enthält das produktive FastAPI-Backend für die Black Six Matrix. Es ist die Abkehr von fiktiven Prompt-Simulationen hin zu einer deterministischen, relationalen Datenbank-Architektur.

## 📁 Projektstruktur

```text
aragon-backend-/
├── main.py                  # Der FastAPI-Server (API-Endpunkte)
├── ingest-registry.py       # Parser-Skript zum Einlesen der Rohdaten in die DB
├── b6_registry.db           # SQLite-Datenbank (Enthält die 100 Entitäten)
├── b6_registry.json         # JSON-Export der Entitäten (Für API-Payloads)
├── aragon_registry_200.csv.md # Quell-Dokumentation der Registry
├── Backend/                 # (Optionaler Ordner für zukünftige Module)
├── requirements.txt         # Python-Dependencies
└── Dockerfile               # Container-Konfiguration für das Deployment
