<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🧩 Ein deklaratives Register und Validator für Adapter externer Maschinen

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only core">
  <img src="https://img.shields.io/badge/Deliveries-4%20of%204-367BF5.svg" alt="4 von 4 Lieferungen">
</p>

> **Status: v0.0.6, Scaffolding - Lieferungen 1-4 von 4 (Schema/CLI/
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

---

## 1. 🛠️ TECHNISCHER ÜBERBLICK

Heute ist die Auswahl und Konfiguration, welche Bridge eine bestimmte
Zelle/Maschine verwendet, über README-Dateien, `.env`-Dateien und Ad-hoc-
Skripte in vielen echten Bridge-Repositories verteilt.
HYDRA-UMC-CONNECTOR-HUB soll der einzige Ort werden, der für jede echte
externe Maschine drei Fragen beantwortet: **Welches Protokoll spricht
sie, was kann sie wirklich tun (lesen/schreiben/abbrechen, mit welchem
Risiko), und welches echte, bereits existierende Projekt dieses
Ökosystems implementiert das bereits?**

Diese Version liefert alle vier Lieferungen dieses Plans:

1. **Ein echter, fester Vertrag** ([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)) -
   das eigene "CONTRATO MINIMO DE ADAPTADOR" des ökosystemweiten Audits,
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

$ hydra-umc-connector-hub gate fixtures/cnc-grbl.json --capability sendControlByte \
    --job-id j1 --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
{"allowed": true, "reason": "cell and external machine are ready", "evidenceErrors": []}

$ hydra-umc-connector-hub certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Juan Enrique" --evidence-file real-status.json --out-dir certifications/
CERTIFIED adapterId='cnc-grbl' certificationId='...' -> certifications/cnc-grbl__....json
```

Es gibt nirgendwo im Projekt eine Standard-/argumentlose Aufrufform
noch eine GUI - siehe
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) für die vollständige,
echte Befehlsoberfläche.

## 2. 🧱 ARCHITEKTUR UND DESIGN-ENTSCHEIDUNGEN

- **Ein handgeschriebener Validator, kein `jsonschema`.** Der eigene
  Vertrag von Lieferung 1 ist klein genug (14 Felder oberster Ebene,
  eine verschachtelte Fähigkeits-Form), dass eine einfache Python-
  Funktion, die echte, spezifische Fehlerzeichenketten sammelt, sowohl
  einfacher als ein generischer JSON-Schema-Validator ist ALS AUCH
  klarere Ausgaben erzeugt - jede Meldung benennt genau das
  betroffene Feld/den Index, keinen generischen Schema-Pfad.
- **Die write/abort-Sicherheitsregel wird im Code durchgesetzt, nicht in
  der Dokumentation.** `_WRITE_CAPABILITY_REQUIRED_FIELDS` in
  `schema.py` ist der eigene explizite Satz des Audits, umgesetzt in
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

## 📂 VERZEICHNISSTRUKTUR

```
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py            # Der echte adapter-manifest-Vertrag + struktureller Validator + JSON-Schema-Teilmengenprüfer
│   ├── registry.py          # Lieferung 2: durchsucht ein Verzeichnis zu einem echten, stabilen, sortierten Katalog
│   ├── catalog_server.py    # Lieferung 2: echter, nur-GET http.server, der den Katalog bereitstellt
│   ├── sdk_gate.py          # Lieferung 3: echte evaluate_job()-Integration von HYDRA-UMC-SDK
│   ├── certification.py     # Lieferung 4: echtes, nur anfügendes, von einem Menschen bezeugtes Zertifizierungsprotokoll
│   └── cli.py               # Einstiegspunkt validate/catalog/serve-catalog/gate/certify/certifications
├── fixtures/                # Zehn echte, gültige Adapter-Manifeste (eines pro existierender Bridge)
│   └── invalid/             # Fünf echte ungültige Manifeste, jedes mit einem eigenen Ablehnungsgrund
├── tests/                   # Echte Tests: Fixtures, ein echter http.server auf einem ephemeren Port, das echte installierte hydra-umc-sdk, und ein echtes Zertifizierungsprotokoll in einem temporären Verzeichnis
├── docs/
│   ├── ADAPTER_MANIFEST.md  # Der vollständige echte Vertrag, Feld für Feld
│   ├── CAPABILITY_GATE.md   # Der eigene echte Schrankenvertrag von Lieferung 3 und seine eine benannte Vereinfachung
│   ├── CERTIFICATION.md     # Der eigene echte Vertrag von Lieferung 4 und seine ehrliche Hardware-Verifizierungslücke
│   └── CLI_REFERENCE.md     # Jeder Unterbefehl, seine Ausgabeformen, der Exit-Code-Vertrag
├── images/                  # Medien und App-Icons
├── tools/
│   ├── build_test.py        # Build-/Kompilierungsprüfung ohne Versionierung
│   └── ci_validate.py       # Manifest-/CHANGELOG-/Doku-Validierung, die von der CI verwendet wird
├── build.sh / build.bat     # venv + editierbare Installation + Compile-Check + Tests
├── build-test.sh / .bat     # Nur Build-Validierung, ohne etwas zu verändern
├── run.sh / run.bat         # Echte Demo: validiert die zehn Fixtures (ohne Argumente), oder leitet einen echten CLI-Befehl weiter
├── bump_version.py          # "Kilometerzähler"-Inkrement des Ökosystems (pyproject.toml + __init__.py)
└── bump_manifest_version.py # Synchronisiert die Version von hydra-umc.project.json mit der nativen (--sync)
```

## ⚙️ BUILD UND AUSFÜHRUNG

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

## 🚀 FAHRPLAN

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

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage eigentlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Direkt verwandt**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag, gegen den jede Bridge bereits ihre eigenen Befehle validiert; der `gate`-Befehl dieses Hubs (Lieferung 3) ruft direkt dessen eigenes echtes `bridge_contract.evaluate_job()` für eine write/abort-Fähigkeit auf, niemals eine zweite Implementierung dieser Schranke.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — das andere vom Audit-Vorschlag empfohlene neue Projekt: betreibt den Wartungsvorfall-Lebenszyklus der eigenen Komponenten dieses Ökosystems, während dieser Hub entdeckt und validiert, was eine EXTERNE Maschine/ein Adapter kann.
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — ausdrücklich NICHT durch dieses Projekt ersetzt: GATEWAY-INDUSTRIAL ist ein echtes Protokoll-Relais mit eigener Befehls-Allowlist; dieser Hub ist ein deklaratives Register/Validator, das über ihm und jeder anderen Bridge sitzt, niemals eine zweite Implementierung eines Protokolls.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware & Plattform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — das physische Motherboard des Roboterarms: CM5-Host + Dual-Core-STM32H745, koordiniert bis zu 8 Werkzeugarme über CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.

*Kern-Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das reale Headless-Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarmleitstand (PySide6) für mehrere Server gleichzeitig.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und einer gekoppelten Wear-OS-Begleit-App.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für das eingebaute 7"-DSI-Touchscreen, direkt auf dem CM5 eingebettet.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in STUDIOs eigenen Katalog überträgt.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen echten VDA-5050-MQTT-Publisher; das echte `ownerProject` hinter dem eigenen `mobile-vda5050`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit echtem GRBL-Status-/Steuerbyte-Zugriff; hinter dem eigenen `cnc-grbl`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem echten Boston-Dynamics-Spot-Befehlssender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Sicherheitskoordinator für Laserzellen, liest 3 echte Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Sicherungen; hinter dem eigenen `laser-safety`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer High-Level-Koordinator für den Leiterplattenfluss von OpenPnP Pick-and-Place; hinter dem eigenen `pnp-openpnp`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsschranke für Moonraker/Klipper-3D-Drucker, mit echten gesicherten Job-Befehlen; hinter dem eigenen `printer-moonraker`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Sicherheitskoordinator mit einem echten, träge importierten rclpy-ROS-2-Transport; hinter dem eigenen `robotics-ros2`-Fixture dieses Hubs.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem echten MAVLink-Befehlssender; hinter dem eigenen `uav-mavlink`-Fixture dieses Hubs.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Platinen, CAN-OTA plus Full-Chip-SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrationsknoten für die Hailo-8-Vision-Pipeline, mit einer echten stufenweisen Hardware-Bereitschaftsprüfung.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echte Registry für kompilierte Modelle mit Hailo-Architektur-/Prüfsummen-Safe-Load-Verifizierung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsschranke.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — echtes Position-Based-Visual-Servoing-Korrekturgesetz, sicherheitsgesteuert nach vorgelagertem Zonenstatus.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — echte Zonenverletzungsprüfung und E-STOP-Anforderung, mit erzwungener Kalibrierungsaktualität.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrationsknoten für die Hailo-10-Cognitive-Pipeline (LLM-/VLA-/Sprach-Orchestrierung).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungsgesicherten Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur auf der Standardbibliothek basierende TF-IDF-Dokumentensuche über die eigenen Markdown-Dokumente dieses Ökosystems.

*Orchestrierung & Schwarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrationsknoten mit einem echten gRPC/Protobuf-Health-Report-Vertrag und einer Missions-Zustandsmaschine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Health-Watchdog mit Retry/Backoff und Identitäts-Mismatch-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet auf Multi-Zellen-Konvergenz.

*Digitaler Zwilling & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrationsknoten für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Sync-Vertrag.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — echte Hardware-in-the-Loop-Sicherheitsverriegelung, die Befehle zwischen Simulation und echter Hardware routet.
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit echten haptischen Alarmen und einem Sprach-Relay zum gekoppelten Telefon.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinenmontagegestell mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.

---

## 📚 Dokumentation & Community

- **[docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)** — der vollständige echte Vertrag, Feld für Feld, und warum `authenticationRef` eine Referenz ist.
- **[docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)** — die eigene echte Integration von Lieferung 3 mit der Sicherheitsschranke von HYDRA-UMC-SDK und ihre eine benannte Vereinfachung.
- **[docs/CERTIFICATION.md](docs/CERTIFICATION.md)** — der eigene echte Zertifizierungsprotokoll-Vertrag von Lieferung 4 und seine ehrliche Hardware-Verifizierungslücke.
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — jeder Unterbefehl, seine Ausgabeformen, und der Exit-Code-Vertrag.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ

GPL-3.0 (Software) / CC BY-SA 4.0 (Dokumentation) - siehe [LICENSE.md](LICENSE.md).
