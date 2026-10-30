<!-- =============================================================================
HYDRA-UMC-CONNECTOR-HUB - Adapter-manifest registry
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🧩 Ein deklaratives Register und Validator für Adapter externer Maschinen

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="Core">
  <img src="https://img.shields.io/badge/Deliveries-4%20of%204-367BF5.svg" alt="Deliveries">
  <img src="https://img.shields.io/badge/Tests-188%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.6-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **Status: v0.1.6, funktional - Lieferungen 1-4 von 4 (Schema/CLI/
> Fixtures, schreibgeschützter Katalog, SDK-Sicherheitsschranke,
> Zertifizierungsdatensätze).** `catalog`/`serve-catalog` sind echt und
> nur GET (es gibt nirgendwo im Projekt einen Schreib-Netzwerkpfad);
> `gate` ruft direkt das eigene echte `evaluate_job()` von HYDRA-UMC-SDK
> auf, niemals eine zweite Implementierung dieser Schranke (siehe
> [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)); `certify`
> zeichnet eine echte, von einem Menschen bezeugte Nachweis-Nutzlast
> auf, verifiziert sie aber ausdrücklich NICHT unabhängig gegen echte
> Hardware - siehe [docs/CERTIFICATION.md](docs/CERTIFICATION.md), warum
> das ohne eine physische Maschine in der Hand außerhalb des Umfangs
> bleibt. Siehe [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) für die
> genaue Befehlsoberfläche, die es heute gibt.

> **Ehrlichkeitscheck - was heute wirklich läuft:** das Manifest-Schema/der Validator (`schema.py`), der schreibgeschützte Katalog (`registry.py`, `catalog_server.py`), die SDK-Sicherheitsgate-Integration (`sdk_gate.py`, die das echte `evaluate_job()` von `HYDRA-UMC-SDK` gegen einen echt installierten Checkout aufruft, nie eine Simulation), das Zertifizierungsprotokoll (`certification.py`) und die CLI (`cli.py`) sind real und durch 188 bestehende Tests abgedeckt (`pytest tests/`, mit dem optionalen Extra `[sdk]` installiert - 34 davon werden ohne es übersprungen). `certify` zeichnet eine von einem Menschen bezeugte Evidenz auf, verifiziert sie aber ausdrücklich nicht unabhängig gegen echte Hardware - hinter keiner der 10 Fixtures steht eine physische Maschine, und kein Adapter hier wurde je genutzt, um tatsächlich mit einem echten Gerät zu sprechen. `catalog`/`serve-catalog` sind konstruktionsbedingt nur GET (`catalog_server.py` hat überhaupt kein `do_POST`/`do_PUT`). Siehe den Status-Kasten oben und `CHANGELOG.md` für das, was bisher genau ausgeliefert wurde.

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem. Es gibt noch keinen Hardware-E-STOP-Pfad, keine von der Firmware durchgesetzten Grenzen oder Verriegelungen und keinen verifizierten Bewegungsbefehl; Firmware-Images werden mit CRC-32 und einer Ed25519-Signatur geprüft, und ein Release-Build verweigert die veröffentlichten Entwicklungsschlüssel (die Werkzeugköpfe und Erweiterungsplatinen hinter dem Relais laufen noch mit URTC-Bootloadern, die statt einer Signatur ein HMAC-SHA256 mit gemeinsamem Schlüssel verwenden); TLS und gegenseitiges TLS sind optional und standardmäßig aus; noch keine eigene Platine wurde bestückt oder getestet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

---

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.1.6` |
| Reifegrad | Funktionsfähig |
| Tests | 188 (`python -m pytest -q tests`) |
| Technik | Python 3.11+ / JSON Schema (hand-written structural validator, no jsonschema dependency) / http.server (stdlib-only real read-only catalog endpoint) / HYDRA-UMC-SDK (optional, real safety-gate integration via evaluate_job()) |
| Ziel | Der PC der Person, die es benutzt |
| Auf echter Hardware | Noch nicht: für diese Version ist kein Lauf auf echter Hardware vermerkt |

**Springe zu:** [Überblick](#-überblick) · [Architektur](#-architektur) · [Sicherheit und Schutz](#-sicherheit-und-schutz) · [Schnittstellen](#-schnittstellen) · [Konfiguration](#-konfiguration) · [Schnellstart](#-schnellstart) · [Tests](#-tests) · [Fehlerbehebung](#-fehlerbehebung) · [Struktur des Repositorys](#-struktur-des-repositorys) · [Verwandte Projekte](#-verwandte-projekte)

## 🚦 Projektstatus

Jede Zeile ist ein Teil dieses Repositorys, und die Ampel sagt, wie weit er heute ist. Sie beruht auf dem, was das Repository zeigen kann (Tests, Builds, Läufe), nicht auf dem, was geplant ist.

🟢 Fertig und überprüft · 🟡 Funktioniert, mit bekannten Grenzen · 🟠 Teilweise fertig oder noch nicht überprüft · 🔴 Nicht gemacht oder funktioniert nicht

| Bereich | Stand | Was das hier bedeutet |
|---|---|---|
| Software | 🟡 | Funktioniert für seinen Hauptzweck; die Ehrlichkeitsprüfung oben nennt, was noch fehlt |
| Tests | 🟢 | 188 automatische Tests, bei jeder Änderung ausgeführt |
| Echte Hardware | 🔴 | Noch nicht: für diese Version ist kein Lauf auf echter Hardware vermerkt |
| Dokumentation | 🟢 | README in acht Sprachen, bei jeder Änderung gegen das Manifest geprüft |

## 🎯 Überblick

Heute ist die Auswahl und Konfiguration, welche Bridge eine bestimmte
Zelle/Maschine verwendet, über README-Dateien, `.env`-Dateien und Ad-hoc-
Skripte in vielen echten Bridge-Repositories verteilt.
HYDRA-UMC-CONNECTOR-HUB soll der einzige Ort werden, der für jede echte
externe Maschine drei Fragen beantwortet: **Welches Protokoll spricht
sie, was kann sie wirklich tun (lesen/schreiben/abbrechen, mit welchem
Risiko), und welches echte, bereits existierende Projekt dieses
Ökosystems implementiert das bereits?**

Diese Version liefert alle vier geplanten Lieferungen, in sechs Teilen:

1. **Ein echter, fester Vertrag** ([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)) -
   das "CONTRATO MINIMO DE ADAPTADOR" dieses Ökosystems,
   mit einer bereits im Code durchgesetzten, nicht verhandelbaren Regel:
   eine `write`/`abort`-Fähigkeit wird abgelehnt, sofern sie nicht auch
   ihr eigenes Risiko, die erforderliche Berechtigung, den erforderlichen
   Zellenzustand, das Erfordernis einer menschlichen Bestätigung und ein
   Zeitlimit deklariert.
2. **Ein echter CLI-Validator** (`hydra-umc-connector-hub validate`) -
   eine handgeschriebene strukturelle Prüfung (ohne `jsonschema`-
   Abhängigkeit), sodass jeder echte Fehler genau den betroffenen
   Adapter/das Feld/die Fähigkeit benennt.
3. **Zehn echte Fixtures**, eine pro bereits existierendem echten
   Bridge-/Protokollprojekt in diesem Ökosystem - der Beweis, dass der
   Vertrag nicht theoretisch ist, und eine Startvorlage für ein neues
   Adapter-Manifest.
4. **Ein echter, schreibgeschützter Katalog** (`catalog`/`serve-catalog`)
   - entdeckt jedes strukturell gültige Manifest in einem Verzeichnis
   und stellt es mit `serve-catalog` über einen echten, nur-GET
   `http.server` bereit (es gibt nirgendwo im Projekt eine
   Schreib-Route).
5. **Eine echte Integration mit der Sicherheitsschranke von
   HYDRA-UMC-SDK** (`gate`) - ein `write`/`abort`-Fähigkeitsaufruf wird
   vom eigenen echten `evaluate_job()` des SDK geschrankt, niemals einer
   zweiten Implementierung dieser Logik; siehe
   [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md).
6. **Echte Zertifizierungsdatensätze** (`certify`/`certifications`) -
   ein echtes, von einem Menschen bezeugtes, nur anfügendes Protokoll,
   geprüft gegen das eigene `evidenceSchema` eines Adapters; siehe
   [docs/CERTIFICATION.md](docs/CERTIFICATION.md), warum die
   unabhängige Verifizierung des Nachweises gegen echte Hardware hier
   ausdrücklich außerhalb des Umfangs bleibt.

```
$ hydra-umc-connector-hub validate fixtures/industrial-opcua.json
VALID fixtures/industrial-opcua.json adapterId='industrial-opcua' ownerProject='HYDRA-UMC-OPCUA-SERVER'

$ hydra-umc-connector-hub catalog --registry-dir fixtures | head -c 200
{"adapters": [{"adapterId": "cnc-grbl", "protocol": "grbl-serial", ...

$ hydra-umc-connector-hub gate fixtures/cnc-grbl.json --capability grblStatus \
    --job-id j1 --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
{"allowed": true, "reason": "read capabilities are not subject to the motion safety gate", "evidenceErrors": []}

$ hydra-umc-connector-hub certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Juan Enrique" --evidence-file real-status.json --out-dir certifications/
CERTIFIED adapterId='cnc-grbl' certificationId='...' -> certifications/cnc-grbl__....json
```

Es gibt nirgendwo im Projekt eine Standard-/argumentlose Aufrufform
noch eine GUI - siehe
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) für die vollständige,
echte Befehlsoberfläche.

## 🧩 Rolle in HYDRA-UMC

**HYDRA-UMC-CONNECTOR-HUB** beschreibt, wie externe Maschinen an das Ökosystem anschließen, ohne sich mit einer zu verbinden. Ein Adapter sagt in einem Manifest, was er ist, was er kann (lesen, schreiben, abbrechen) und wie er sich authentifiziert; der Hub prüft es, listet es, schickt eine angeforderte Fähigkeit durch das echte SDK-Tor und führt Protokoll darüber, wer was zertifiziert hat.

## 🏛️ Architektur

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-CONNECTOR-HUB architecture" width="100%">
</p>

**Warum es so gebaut ist**

- **Ein handgeschriebener Validator, kein `jsonschema`.** Der eigene
  Vertrag von Lieferung 1 ist klein genug (14 Felder oberster Ebene,
  eine verschachtelte Fähigkeits-Form), dass eine einfache Python-
  Funktion, die echte, spezifische Fehlerzeichenketten sammelt, sowohl
  einfacher als ein generischer JSON-Schema-Validator ist ALS AUCH
  klarere Ausgaben erzeugt - jede Meldung benennt genau das
  betroffene Feld/den Index, keinen generischen Schema-Pfad.
- **Die write/abort-Sicherheitsregel wird im Code durchgesetzt, nicht in
  der Dokumentation.** `_WRITE_CAPABILITY_REQUIRED_FIELDS` in
  `schema.py` ist diese explizite Regel, umgesetzt in
  eine echte, getestete Prüfung - wer ein Manifest schreibt, kann sie
  nicht vergessen, weil der Validator eine Fähigkeit ablehnt, die es
  tut.
- **`authenticationRef` wird als Referenz geprüft, niemals als
  Freitext akzeptiert.** Ein geschlossenes Set echter Präfixe (`env:`,
  `secret-store:`, `vault:`, `none:`) - bewusst keine "sieht wie ein
  Geheimnis aus"-Heuristik (siehe das eigene `log_redaction.py` von
  HYDRA-UMC-OPS-AGENT dafür, warum eine Heuristik auch hier für genau
  dasselbe Problem das falsche Werkzeug ist).
- **Jeder Fehler wird gesammelt, niemals nur der erste.**
  `validate_adapter_manifest()` prüft weiter, nachdem ein Problem
  gefunden wurde - wer ein Manifest korrigiert, sieht alle echten
  Probleme in einem einzigen Durchlauf.
- **Der Katalog ist absichtlich echt und schreibgeschützt.**
  `registry.py` durchsucht ein Verzeichnis ohne Rekursion (sodass ein
  verschachteltes `fixtures/invalid/` niemals einem echten Katalog
  beitritt), verwirft - meldet aber weiterhin - alles, was
  `validate_adapter_manifest()` nicht besteht, und lehnt zwei Dateien
  ab, die dieselbe `adapterId` deklarieren. `catalog_server.py` hat
  nirgendwo ein `do_POST`/`do_PUT` - ein Schreibversuch erhält das
  eigene ehrliche `501` von `BaseHTTPRequestHandler`, niemals eine
  Route, die dieses Projekt zu schützen vergessen hat.
- **Die Sicherheitsschranke nutzt die eigene echte Logik von
  HYDRA-UMC-SDK wieder, niemals eine zweite Implementierung davon.**
  Das `evaluate_capability_call()` von `sdk_gate.py` ruft direkt
  `hydra_umc_sdk.bridge_contract.evaluate_job()` für jede
  `write`/`abort`-Fähigkeit auf - eine `read`-Fähigkeit berührt das SDK
  nie, da `evaluate_job()` eine Bewegungs-/Schreibschranke ist, keine
  Leseschranke. Siehe
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) für die eine
  bewusste, benannte Vereinfachung, die diese Integration vornimmt (ein
  einzelner Ersatz-`JobPhase` für jede Schreibaktion, die kein Abbruch
  ist).
- **Ein Zertifizierungsdatensatz ist ehrlich darüber, was er beweisen
  kann und was nicht.** `certification.py` verweigert das Speichern
  einer Zertifizierung, deren Nachweis nicht zum eigenen
  `evidenceSchema` des Adapters passt, behauptet aber nie, unabhängig
  zu verifizieren, dass dieser Nachweis von echter Hardware stammt - es
  gibt nirgendwo in diesem Projekt einen Codepfad, der eine echte
  serielle Schnittstelle/OPC-UA-Sitzung/MQTT-Verbindung öffnet, um das
  zu prüfen. Siehe [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Die zehn Fixtures nennen echte Eigentümerprojekte, niemals
  erfundene.** Jedes `ownerProject` in `fixtures/*.json` ist ein echtes
  Repository dieses Ökosystems (siehe den Abschnitt Verwandte Projekte)
  - dies ist eine echte Registervorlage, keine spekulative.
- **Nur Standardbibliothek für den Kern.**
  `validate`/`catalog`/`serve-catalog`/`certify`/`certifications`
  benötigen keine Abhängigkeit - `json`, einfaches Python für die
  strukturellen Prüfungen und `http.server`. Nur `gate` bei einer
  `write`/`abort`-Fähigkeit benötigt das optionale `[sdk]`-Extra.

## 🔒 Sicherheit und Schutz

| Bedrohung | Abwehr | Wo |
|---|---|---|
| Ein Adapter, der sich als anderes Projekt ausgibt | Das Eigentümerprojekt muss `^(HYDRA-UMC\|URTC)(-[A-Z0-9-]+)?$` entsprechen und wird mit `--ecosystem-root` gegen das `hydra-umc.project.json` dieses Repositorys geprüft | `schema.py`, `cli.py` |
| Zugangsdaten in einem Manifest, ein riesiges Manifest, ein unbekannter Modus | `authenticationRef` erlaubt nur die Präfixe `env:`, `secret-store:`, `vault:` oder `none:` (nie das Geheimnis selbst); ein Manifest hat höchstens 1 000 000 Byte; die Fähigkeitsmodi sind `read`, `write` und `abort`, die Idempotenz ist `none`, `idempotent`, `at-least-once` oder `exactly-once` | `schema.py` |
| Einen Adapter ohne das Tor aufrufen, eine alte Anfrage | `gate` ruft das eigene `evaluate_job()` des SDK auf und nie eine zweite Implementierung; es braucht `--allow-unobserved`, um einem erklärten Zustand zu trauen, und `--human-confirmed`, `--safety-gate` und `--permission`, wie das Manifest es verlangt; eine Anfrage, die älter als 30 Sekunden oder mehr als 5 Sekunden voraus ist, wird abgelehnt | `sdk_gate.py`, `cli.py` |
| Manipulierte Zertifizierungsprotokolle und ein Schreibzugriff übers Netz | Die Protokolle bilden eine Hash-Kette, versiegelt mit einem Schlüssel von mindestens 16 Zeichen (`.chain-head.json`, `.chain.lock`), und `verify --strict` schlägt bei einem Eintrag außerhalb der Kette fehl; `catalog` und `serve-catalog` sind nur GET: Im Projekt gibt es keinen Schreibweg übers Netz | `ledger.py`, `catalog_server.py` |

**Was er nie tut:** er berührt nie eine Maschine, und eine Zertifizierung speichert, was eine Person bezeugt: Die Nachweise werden nicht gegen echte Hardware geprüft (siehe `docs/CERTIFICATION.md`).

## 🔌 Schnittstellen

Der Befehl `hydra-umc-connector-hub` (oder `./run.sh`); die vollständige Referenz ist `docs/CLI_REFERENCE.md`. Der Katalog wird auch per HTTP ausgeliefert, nur GET, standardmäßig auf `127.0.0.1:8801`.

| Topic oder Route | Was es trägt |
|---|---|
| `validate MANIFEST...` | Manifeste gegen den Vertrag prüfen |
| `catalog --registry-dir DIR`, `serve-catalog --registry-dir DIR --port 8801` | die Adapter auflisten oder dieselbe Liste per GET ausliefern (`--ecosystem-root` prüft zusätzlich die Eigentümerprojekte) |
| `gate MANIFEST --capability ... --job-id ... --idempotency-key ... --source ... --cell-state ... --machine-state ...` | eine Fähigkeit durch das SDK-Tor schicken (`--param k=v`, `--evidence-file`, `--allow-unobserved`, `--human-confirmed`, `--safety-gate`, `--permission`) |
| `certify`, `certifications`, `verify --strict` | die Bezeugung einer Person in der Hash-Kette festhalten, die Protokolle auflisten, die Kette prüfen |

## ⚙️ Konfiguration

Es gibt keine eigenen Umgebungsvariablen: Registry-Ordner, Host und Port des Katalogs (`--registry-dir`, `--host`, `--port`) und der Schlüssel der Zertifizierungskette (mindestens 16 Zeichen) sind Kommandozeilenargumente. Die Zugangsdaten eines Adapters stehen nie in seinem Manifest, nur ein Verweis darauf, wo sie liegen.

## 🚀 Schnellstart

Benötigt Python 3.11 oder neuer; der Kern nutzt nur die Standardbibliothek (das Extra `sdk`, `pip install -e ".[sdk]"`, braucht nur `gate` bei einer Schreib- oder Abbruchfähigkeit).

```bash
chmod +x build.sh   # einmalig
./build.sh          # erstellt .venv, pip install -e ".[dev]", Compile-Check + Tests
./run.sh                                   # echte Demo: validiert die zehn echten Fixtures
./run.sh validate fixtures/industrial-opcua.json
./run.sh validate fixtures/invalid/*.json  # jedes davon sollte INVALID melden
./run.sh catalog --registry-dir fixtures
./run.sh serve-catalog --registry-dir fixtures --port 8801   # Strg+C zum Stoppen
pip install -e ".[sdk]"                    # nur für `gate` bei einer write/abort-Fähigkeit nötig
./run.sh gate fixtures/cnc-grbl.json --capability sendControlByte --job-id j1 \
    --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
./run.sh certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Ihr Name" --evidence-file real-status.json --out-dir certifications/
```

Unter Windows: `build.bat`, dann `run.bat` (dieselbe Demo ohne
Argumente) / einer der obigen Unterbefehle. `build-test.sh`/`.bat`
führt dieselbe Kompilierungsprüfung (nur Python-Syntax) aus, ohne die
Projektversion oder das CHANGELOG anzufassen, die die eigene CI dieses
Projekts auch ausführt - es führt NICHT selbst die Testsuite aus; die
CI führt `pytest` als eigenen, späteren Schritt aus. Führen Sie
`./build.sh`/`build.bat` (oder direkt `pytest tests/`) für die
vollständige lokale Testsuite aus.

**Fehlerbehebung**

- `validate` meldet `INVALID` für ein Manifest, das Sie für korrekt
  halten: Lesen Sie jeden aufgeführten Grund - der Validator meldet
  alle, nicht nur den ersten. Siehe
  [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md) für den genauen
  Vertrag Feld für Feld.
- `validate` meldet `ERROR: ... is not valid JSON`: Die Datei selbst ist
  fehlerhaftes JSON, zu unterscheiden von einem wohlgeformten, aber
  ungültigen Manifest - prüfen Sie auf ein fehlendes Komma/Anführungs-
  zeichen, bevor Sie den Vertrag selbst prüfen.
- `catalog`/`serve-catalog` endet mit Exit-Code `1` oder listet eine
  Datei unter `invalidFiles`: diese Datei hat die strukturelle
  Validierung nicht bestanden und wurde absichtlich aus dem Katalog
  ausgeschlossen - führen Sie `validate` direkt darauf aus, um die
  vollständige Liste der Gründe zu sehen.
- `gate` schlägt fehl mit `ERROR: the optional 'hydra-umc-sdk' package
  is not installed`: Führen Sie zuerst `pip install -e ".[sdk]"` aus -
  nur für eine `write`/`abort`-Fähigkeit nötig.
- `gate`/`certify` schlägt fehl mit `ERROR: unknown cell_state ...`
  oder `... does not match evidenceSchema`: Siehe
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)/
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md) für die genauen
  erwarteten Werte/Formen.

## 🧪 Tests

188 automatische Tests laufen mit `python -m pytest -q tests` (39 davon brauchen das Extra `sdk` und werden ohne es übersprungen): das Schema und das veröffentlichte JSON-Schema, der Katalog, das SDK-Tor, die Zertifizierungskette, die Kommandozeile und feindliche Eingaben. Keine Hardware, kein äußeres Netz.

Die CI führt `HYDRA_UMC_CI=1 python tools/ci_validate.py` aus; das prüft das Manifest, die Dokumente, die acht READMEs und die Bilder.

## 🏗️ Build und Veröffentlichung

Für eine Veröffentlichung gibt es nichts zu kompilieren: `build.sh` / `build.bat` legen die virtuelle Umgebung an, installieren das Paket im editierbaren Modus und führen die Tests aus, `build-test` prüft nur. Bauen ändert nie die Version; sie wird nur von `python tools/hydra_project_tool.py bump` erhöht, das auch das Änderungsprotokoll fortschreibt. Die Version von Paket, Manifest und Änderungsprotokoll muss übereinstimmen, sonst schlägt `ci_validate.py` fehl.

## 🩺 Fehlerbehebung

| Du siehst | Weil | Tu |
|---|---|---|
| `INVALID` on a manifest | Das Manifest verletzt den Vertrag: ein falsches Eigentümerprojekt, ein Geheimnis in `authenticationRef`, ein unbekannter Modus oder mehr als 1 000 000 Byte | Lies die Meldung von `validate`; `./run.sh validate fixtures/invalid/*.json` zeigt jede Art von Fehler |
| `gate` refuses a write or abort capability | Das SDK ist nicht installiert, oder der Zustand wurde nicht beobachtet, oder eine vom Manifest verlangte Bestätigung fehlt | `pip install -e ".[sdk]"`; gib `--observed-machine-state` an, oder `--allow-unobserved`, wenn du den erklärten Zustand hinnimmst; füge `--human-confirmed`, `--safety-gate` und `--permission` nach Bedarf hinzu |
| `verify --strict` fails | Ein Zertifizierungsprotokoll liegt außerhalb der Hash-Kette oder der Schlüssel ist falsch | Nimm den Schlüssel, mit dem die Kette versiegelt wurde (mindestens 16 Zeichen); ein von Hand hinzugefügter oder geänderter Eintrag liegt konstruktionsbedingt außerhalb der Kette |

## 📂 Struktur des Repositorys

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-CONNECTOR-HUB" width="100%">
</p>

<details>
<summary>Textversion des Baums</summary>

```text
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py                                der Adapter-Manifest-Vertrag und sein Prüfer
│   ├── registry.py                              meldet die echten Bridges als Adapter an
│   ├── catalog_server.py                        der Katalog-Endpunkt nur mit GET
│   ├── sdk_gate.py                              ruft das eigene evaluate_job() des SDK auf
│   ├── certification.py ledger.py               Zertifizierungsprotokolle in einer versiegelten Hash-Kette
│   └── cli.py                                   validate, catalog, serve-catalog, gate, certify
├── tests/                                       188 Tests
├── docs/                                        Leitfäden zu Manifest, Tor, Zertifizierung und Reife
├── fixtures/                                    zehn echte Adapter-Manifeste und die ungültigen
├── schemas/                                     das veröffentlichte JSON-Schema
├── tools/                                       Build- und Testläufer, Versionserhöhung, CI-Prüfer, README- und Bildgeneratoren samt Prüfungen
├── images/                                      Banner und die Bilder der README
├── .github/                                     CI-Workflow und Issue-Vorlagen
├── pyproject.toml                               Paketmetadaten und Abhängigkeiten
├── hydra-umc.project.json                       Manifest: Version, Reifegrad, Familie
├── CHANGELOG.md                                 was sich in jeder Version geändert hat
├── build.sh build.bat                           Build-Skripte (ändern die Version nie)
├── build-test.sh build-test.bat                 Build-Skripte (ändern die Version nie)
├── test.sh test.bat                             führen die Tests aus
├── bump_version.py / bump_manifest_version.py   ausdrückliche Versionserhöhung
├── run.sh run.bat                               die Demo und die Befehle
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE LICENSE.md
```

</details>

## 🗺️ Roadmap und bekannte Grenzen

**Bekannte Grenzen heute**

Alle vier Lieferungen des im eigenen Manifest und CHANGELOG dieses
Projekts benannten Plans liefern jetzt echten, getesteten Code. Was
bleibt, ehrlich gesagt:

- **Die Hardware-Verifizierungslücke von Lieferung 4 bleibt absichtlich
  offen.** `certify` zeichnet einen von einem Menschen bezeugten
  Nachweis auf, geprüft gegen das eigene `evidenceSchema` eines
  Adapters, aber nichts in diesem Projekt bestätigt unabhängig, dass
  dieser Nachweis tatsächlich von der genannten echten Maschine stammt
  - das erfordert die physische Hardware selbst, in einer echten Zelle,
  die diese Entwicklungsmaschine nicht besitzt. Siehe
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Integration mit einem echten Client: begonnen, nicht abgeschlossen.**
  HYDRA-UMC-SERVER fragt `serve-catalog` jetzt wirklich ab -
  `GET /api/adapters` und `GET /api/adapters/:adapterId` leiten den
  echten Katalog dieses Projekts durch, Ende zu Ende (siehe das eigene
  `tools/verify_connector_hub_relay_contract.mjs` von HYDRA-UMC-SERVER,
  das den echten `serve-catalog` dieses Projekts gegen dessen echte
  `fixtures/` und eine echte Server-Instanz startet, nie einen Mock). Es
  wurde außerdem als echtes Wheel in ein venv außerhalb des eigenen
  Checkouts dieses Projekts installiert und von dort ausgeführt, was
  bestätigt, dass das Packaging selbst (nicht nur eine editierbare
  Installation) funktioniert. Dass Studio/Suite/Updater `gate` selbst
  aufrufen, bleibt echte, separate, zukünftige Arbeit.
- **Ein echter Transport zwischen einem `gate`/`certify`-Aufrufer und
  dem echten Zellen-/Maschinenzustand fehlt.** Heute werden
  `--cell-state`/`--machine-state` vom Aufrufer als bereits bekannte
  Werte übergeben - es gibt hier keinen Codepfad, der sie live von
  HYDRA-UMC-SERVER oder einem Sicherheitszonen-Dienst abruft.

## 🌍 Sprachen

Diese README und die Dokumente des Repositorys gibt es in acht Sprachen: Englisch, Spanisch, Deutsch, Französisch, Italienisch, Japanisch, Chinesisch und Portugiesisch (Portugal). Sie entstehen gemeinsam, und die CI prüft, dass die acht Dateien dieselben Abschnitte und dieselben Links haben. Dieses Repository hat weder eine eigene Oberfläche noch einen eigenen Meldungskatalog, es gibt also keine Oberflächentexte zu übersetzen.

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage eigentlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Direkt verwandt**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag, gegen den jede Bridge bereits ihre eigenen Befehle validiert; der `gate`-Befehl dieses Hubs (Lieferung 3) ruft direkt dessen eigenes echtes `bridge_contract.evaluate_job()` für eine write/abort-Fähigkeit auf, niemals eine zweite Implementierung dieser Schranke.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — ein verwandtes neues Projekt: betreibt den Wartungsvorfall-Lebenszyklus der eigenen Komponenten dieses Ökosystems, während dieser Hub entdeckt und validiert, was eine EXTERNE Maschine/ein Adapter kann.
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — ausdrücklich NICHT durch dieses Projekt ersetzt: GATEWAY-INDUSTRIAL ist ein echtes Protokoll-Relais mit eigener Befehls-Allowlist; dieser Hub ist ein deklaratives Register/Validator, das über ihm und jeder anderen Bridge sitzt, niemals eine zweite Implementierung eines Protokolls.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware & Plattform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — der Entwurf des Motherboards des Roboterarms: CM5-Host + Dual-Core-STM32H745, gedacht zur Koordination von bis zu 8 Werkzeugarmen über CAN-OTA/SPI-OTA (Firmware in einer frühen Phase; noch keine bestückte Platine).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.

*Kern-Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das reale Headless-Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarmleitstand (PySide6) für mehrere Server gleichzeitig.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und einer gekoppelten Wear-OS-Begleit-App.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für das eingebaute 7"-DSI-Touchscreen, direkt auf dem CM5 eingebettet.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in STUDIOs eigenen Katalog überträgt.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — Desktop-STL-Modelleditor, der echte Teile im selben Modellkatalog transformiert/ersetzt/entfernt/hinzufügt, den auch HYDRA-UMC-EDITOR-URDF bearbeitet.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen VDA-5050-MQTT-Publisher (nur gegen eine emulierte Flotte getestet); das echte `ownerProject` hinter dem eigenen `mobile-vda5050`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit GRBL-Status-/Steuerbyte-Zugriff (nur gegen einen Emulator getestet); hinter dem eigenen `cnc-grbl`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem Boston-Dynamics-Spot-Befehlssender (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Koordinator für Laserzellen, liest 3 Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Signale (nur gegen einen simulierten Chip getestet; kann keinen Laser scharfschalten oder auslösen); hinter dem eigenen `laser-safety`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer High-Level-Koordinator für den Leiterplattenfluss von OpenPnP Pick-and-Place; hinter dem eigenen `pnp-openpnp`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsschranke für Moonraker/Klipper-3D-Drucker, mit echten gesicherten Job-Befehlen; hinter dem eigenen `printer-moonraker`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Koordinator mit einem träge importierten rclpy-ROS-2-Transport (noch nicht gegen eine ROS-2-Installation ausgeführt); hinter dem eigenen `robotics-ros2`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem MAVLink-Befehlssender (nur gegen einen Emulator getestet); hinter dem eigenen `uav-mavlink`-Fixture dieses Hubs.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Platinen, CAN-OTA plus Full-Chip-SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — Gateway vor dem CAN-Bus von URTC: Liste erlaubter Kennungen, Ratenbegrenzung und Sitzungsschlüssel; Software auf dem Computer getestet, noch nicht an einem echten Bus.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrationsknoten für die Hailo-8-Vision-Pipeline, mit einer echten stufenweisen Hardware-Bereitschaftsprüfung.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echte Registry für kompilierte Modelle mit Hailo-Architektur-/Prüfsummen-Safe-Load-Verifizierung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsschranke.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based-Visual-Servoing-Korrekturgesetz mit Freigabe abhängig vom Zonenstatus; noch keine Posenschätzung per Kamera.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — v0-Logik für Zonenverletzung, Kalibrierungsaktualität und E-STOP-Anforderung, die Objektpositionen aus einer Datei nimmt; kein Detektor speist sie, und noch kein physischer E-STOP ist angeschlossen.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrationsknoten für die Hailo-10-Cognitive-Pipeline (LLM-/VLA-/Sprach-Orchestrierung).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungsgesicherten Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur auf der Standardbibliothek basierende TF-IDF-Dokumentensuche über die eigenen Markdown-Dokumente dieses Ökosystems.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — lokaler, richtlinien-gesteuerter KI-Wartungstechniker für das Ökosystem selbst - beobachtet, diagnostiziert und schlägt Korrekturen vor; die zwei höchsten Risikostufen sind absichtlich noch nicht implementiert.

*Orchestrierung & Schwarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrationsknoten mit einem echten gRPC/Protobuf-Health-Report-Vertrag und einer Missions-Zustandsmaschine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Health-Watchdog mit Retry/Backoff und Identitäts-Mismatch-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet auf Multi-Zellen-Konvergenz.

*Digitaler Zwilling & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrationsknoten für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Sync-Vertrag.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — Hardware-in-the-Loop-Router mit einer Software-Kollisionsverriegelung zwischen Simulation und echter Hardware (ohne echte Hardware getestet).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzenvalidierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO/COCO-Annotationsexport.

*Daten & Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Abfrage-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Basislinien-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über den DATALAKE-Verlauf, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN/WebSocket-Ingestion-Pipeline in DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Binärprotokoll-Client-Session; das echte `ownerProject` hinter dem eigenen `industrial-opcua`-Fixture dieses Hubs.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Pro-Client-Authentifizierung und Topic-ACLs; hinter dem eigenen `industrial-mqtt`-Fixture dieses Hubs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-`/probe`- und `/current`-XML-Endpunkte mit Degraded-Mode-Ausgabe; hinter dem eigenen `manufacturing-mtconnect`-Fixture dieses Hubs.

*Ökosystembetrieb*
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — erkennt, installiert und aktualisiert jeden Checkout des Ökosystems.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — baut ein neues, vollständig aktuelles CM5-Image.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproduzierbarer Entwicklungshost (Raspberry Pi 5 / CM5), der den Quellcode des Ökosystems vorhält und begrenzte Build-/Test-Aufgaben über eine dauerhafte Warteschlange ausführt; eine dedizierte Entwicklerrolle, ausdrücklich kein operativer CM5.
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit haptischen Alarmmustern und einem Sprach-Relay zum gekoppelten Telefon (noch nicht auf einer physischen Uhr ausgeführt).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinenmontagegestell mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.

## 📚 Dokumentation

Hier steht mehr:

* [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md) - der Adapter-Manifest-Vertrag Feld für Feld
* [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) - wie eine Fähigkeit das SDK-Tor durchläuft
* [docs/CERTIFICATION.md](docs/CERTIFICATION.md) - was ein Zertifizierungsprotokoll ist und was nicht
* [docs/MATURITY_CRITERIA.md](docs/MATURITY_CRITERIA.md) - wann ein Adapter als reifer gilt
* [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) - jeder Befehl und jede Option, mit echter aufgezeichneter Ausgabe
* [Sicherheitsgrundlage des Ökosystems](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Bedrohungsmodell des Ökosystems](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Änderungsprotokoll dieses Repositorys](CHANGELOG.md)
* [Lizenz dieses Repositorys](LICENSE.md)

## 🤝 Mitwirken und Community

* Führe vor einem Pull Request `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (oder `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`) aus: Es muss `CI_VALIDATION=PASS` ausgeben. Führe dafür nicht `build.sh` oder `build.bat` aus; Bauen ist keine Prüfung.
* Die acht READMEs entstehen aus einer einzigen Quelle in HYDRA-UMC-DOCS; bearbeite sie nicht von Hand. Ändere die Quelle und schreibe sie mit `tools/make_readmes.py` neu.
* Behaupte in einer README nichts, was nicht gelaufen ist: Schreibe „simuliert“ oder „nicht auf Hardware erprobt“, wo das stimmt.
* Siehe [CONTRIBUTING.md](CONTRIBUTING.md), den [Verhaltenskodex](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) und [SUPPORT.md](SUPPORT.md).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - [LICENSE](LICENSE).
