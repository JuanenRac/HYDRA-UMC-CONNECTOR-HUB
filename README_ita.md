<!-- =============================================================================
HYDRA-UMC-CONNECTOR-HUB - Adapter-manifest registry
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | 🇮🇹 <b>Italiano</b> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🧩 Un registro dichiarativo e un validatore per adattatori di macchine esterne

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="Core">
  <img src="https://img.shields.io/badge/Deliveries-4%20of%204-367BF5.svg" alt="Deliveries">
  <img src="https://img.shields.io/badge/Tests-188%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **Stato: v0.1.5, functional - Consegne 1-4 di 4 (schema/CLI/fixture,
> catalogo di sola lettura, cancello di sicurezza SDK, registri di
> certificazione).** `catalog`/`serve-catalog` sono reali e solo GET
> (non esiste alcuna rotta di scrittura di rete in nessuna parte di
> questo progetto); `gate` chiama direttamente il proprio `evaluate_job()`
> reale di HYDRA-UMC-SDK, mai una seconda implementazione di quel
> cancello (vedi
> [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)); `certify`
> registra un'evidenza reale attestata da un umano ma esplicitamente NON
> la verifica in modo indipendente contro hardware reale - vedi
> [docs/CERTIFICATION.md](docs/CERTIFICATION.md) per capire esattamente
> perché ciò resta fuori dall'ambito senza una macchina fisica a
> disposizione. Vedi [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) per
> la superficie di comandi esatta che esiste oggi.

> **Verifica di onestà - cosa funziona davvero oggi:** lo schema/validatore di manifest (`schema.py`), il catalogo di sola lettura (`registry.py`, `catalog_server.py`), l'integrazione del gate di sicurezza dell'SDK (`sdk_gate.py`, che chiama il vero `evaluate_job()` proprio di `HYDRA-UMC-SDK` contro un checkout realmente installato, mai una simulazione), il registro di certificazione (`certification.py`), e la CLI (`cli.py`) sono reali e coperti da 188 test superati (`pytest tests/`, con l'extra opzionale `[sdk]` installato - 34 vengono saltati senza). `certify` registra un'evidenza attestata da un umano ma esplicitamente non la verifica in modo indipendente contro hardware reale - non esiste alcuna macchina fisica dietro nessuna delle 10 fixture, e nessun adattatore qui è mai stato usato per parlare realmente con un dispositivo reale. `catalog`/`serve-catalog` sono di sola GET per costruzione (`catalog_server.py` non ha alcun `do_POST`/`do_PUT`). Vedi il riquadro Stato qui sopra e `CHANGELOG.md` per cosa è stato esattamente consegnato finora.

> **Stato di sicurezza (safety e security):** questo ecosistema non è un sistema di sicurezza certificato. Non esiste ancora un percorso E-STOP hardware, né limiti o interblocchi imposti dal firmware, né un comando di movimento verificato; le immagini firmware sono controllate con CRC-32 e una firma Ed25519, e una compilazione di rilascio rifiuta le chiavi di sviluppo pubblicate (le teste utensile e le schede di espansione dietro il relè usano ancora i bootloader di URTC, che accettano un HMAC-SHA256 a chiave condivisa invece di una firma); TLS e TLS reciproco sono opzionali e disattivati per impostazione predefinita; nessuna scheda propria è stata ancora assemblata o provata. Leggi la [base di sicurezza](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e il [modello delle minacce](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) prima di fidarti di qualsiasi affermazione qui per la sicurezza di una persona.

---

## 📋 In breve

| | |
|---|---|
| Versione | `0.1.5` |
| Maturità | Funzionale |
| Test | 188 (`python -m pytest -q tests`) |
| Tecnologia | Python 3.11+ / JSON Schema (hand-written structural validator, no jsonschema dependency) / http.server (stdlib-only real read-only catalog endpoint) / HYDRA-UMC-SDK (optional, real safety-gate integration via evaluate_job()) |
| Destinazione | Il PC di chi lo usa |
| Su hardware reale | Non ancora: per questa versione non risulta alcuna esecuzione su hardware reale |

**Vai a:** [Panoramica](#-panoramica) · [Architettura](#-architettura) · [Sicurezza e protezione](#-sicurezza-e-protezione) · [Interfacce](#-interfacce) · [Configurazione](#-configurazione) · [Avvio rapido](#-avvio-rapido) · [Test](#-test) · [Risoluzione dei problemi](#-risoluzione-dei-problemi) · [Struttura del repository](#-struttura-del-repository) · [Progetti correlati](#-progetti-correlati)

## 🚦 Stato del progetto

Ogni riga è una parte di questo repository e il semaforo dice a che punto è oggi. È scritta in base a ciò che il repository può mostrare (test, compilazioni, esecuzioni), non a ciò che è previsto.

🟢 Fatto e verificato · 🟡 Funziona, con limiti noti · 🟠 Fatto a metà o non ancora verificato · 🔴 Non fatto o non funzionante

| Area | Stato | Cosa significa qui |
|---|---|---|
| Software | 🟡 | Funziona per il suo scopo principale; la verifica di onestà qui sopra elenca ciò che manca ancora |
| Test | 🟢 | 188 test automatici, eseguiti a ogni modifica |
| Hardware reale | 🔴 | Non ancora: per questa versione non risulta alcuna esecuzione su hardware reale |
| Documentazione | 🟢 | README in otto lingue, verificato rispetto al manifesto a ogni modifica |

## 🎯 Panoramica

Oggi, scegliere e configurare quale bridge usa una data cella/macchina è
distribuito tra README, file `.env` e script ad-hoc in molti repository
di bridge reali. HYDRA-UMC-CONNECTOR-HUB è pensato per diventare l'unico
posto che risponde, per qualsiasi macchina esterna reale, a tre
domande: **quale protocollo parla, cosa può davvero fare
(leggere/scrivere/abortire, con quale rischio), e quale progetto reale
già esistente di questo ecosistema lo implementa già?**

Questa versione spedisce tutte e quattro le consegne previste, in sei parti:

1. **Un contratto reale e fisso** ([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)) -
   il "CONTRATO MINIMO DE ADAPTADOR" di questo
   ecosistema, con una regola non negoziabile già applicata nel
   codice: una capacità `write`/`abort` viene rifiutata a meno che non
   dichiari anche il proprio rischio, il permesso richiesto, lo stato di
   cella richiesto, il requisito di conferma umana e il timeout.
2. **Un vero validatore CLI** (`hydra-umc-connector-hub validate`) - un
   controllo strutturale scritto a mano (senza dipendenza
   `jsonschema`), così ogni errore reale nomina l'esatto
   adattatore/campo/capacità responsabile.
3. **Dieci fixture reali**, una per ogni progetto di bridge/protocollo
   già esistente in questo ecosistema - prova che il contratto non è
   teorico, e un modello di partenza per un nuovo manifesto adattatore.
4. **Un vero catalogo di sola lettura** (`catalog`/`serve-catalog`) -
   scopre ogni manifesto strutturalmente valido in una directory e, con
   `serve-catalog`, lo espone tramite un vero `http.server` solo GET
   (non esiste nessuna rotta di scrittura in nessuna parte di questo
   progetto).
5. **Una vera integrazione con il cancello di sicurezza di
   HYDRA-UMC-SDK** (`gate`) - una chiamata a una capacità
   `write`/`abort` è arbitrata dal proprio `evaluate_job()` reale
   dell'SDK, mai una seconda implementazione di quella logica; vedi
   [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md).
6. **Veri registri di certificazione** (`certify`/`certifications`) -
   un registro reale, attestato da un umano e solo in aggiunta,
   verificato contro il proprio `evidenceSchema` di un adattatore; vedi
   [docs/CERTIFICATION.md](docs/CERTIFICATION.md) per capire perché
   verificare l'evidenza in modo indipendente contro hardware reale
   resta esplicitamente fuori dall'ambito qui.

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

Non esiste nessuna invocazione predefinita/senza argomenti né alcuna GUI
in nessuna parte di questo progetto - vedi
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) per la superficie di
comandi completa e reale.

## 🧩 Ruolo in HYDRA-UMC

**HYDRA-UMC-CONNECTOR-HUB** descrive come le macchine esterne si collegano all'ecosistema, senza collegarsi a nessuna. Un adattatore dice in un manifesto cos'è, cosa sa fare (leggere, scrivere, interrompere) e come si autentica; l'hub lo valida, lo elenca, fa passare una capacità richiesta dalla vera porta dell'SDK e tiene un registro di chi ha certificato cosa.

## 🏛️ Architettura

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-CONNECTOR-HUB architecture" width="100%">
</p>

**Perché è fatto così**

- **Un validatore scritto a mano, non `jsonschema`.** Il proprio
  contratto della Consegna 1 è abbastanza piccolo (14 campi di primo
  livello, una forma di capacità annidata) perché una semplice funzione
  Python che raccoglie stringhe di errore reali e specifiche sia allo
  stesso tempo più semplice di un validatore JSON-Schema generico E
  produca un output più chiaro - ogni messaggio nomina l'esatto
  campo/indice responsabile, non un percorso di schema generico.
- **La regola di sicurezza write/abort è applicata nel codice, non nella
  documentazione.** `_WRITE_CAPABILITY_REQUIRED_FIELDS` in `schema.py` è
  quella regola esplicita trasformata in un controllo
  reale e testato - chi scrive un manifesto non può dimenticarla, perché
  il validatore rifiuta una capacità che lo fa.
- **`authenticationRef` viene controllato come un riferimento, mai
  accettato come testo libero.** Un insieme chiuso di veri prefissi
  (`env:`, `secret-store:`, `vault:`, `none:`) - deliberatamente non
  un'euristica "sembra un segreto" (vedi il proprio `log_redaction.py`
  di HYDRA-UMC-OPS-AGENT per capire perché un'euristica è lo strumento
  sbagliato anche qui per esattamente lo stesso problema).
- **Ogni errore viene raccolto, mai solo il primo.**
  `validate_adapter_manifest()` continua a controllare dopo aver trovato
  un problema - chi corregge un manifesto vede tutti i problemi reali in
  un'unica esecuzione.
- **Il catalogo è reale e di sola lettura, deliberatamente.**
  `registry.py` scansiona una directory senza ricorsione (così una
  `fixtures/invalid/` annidata non entra mai in un vero catalogo),
  scarta - ma continua a riportare - tutto ciò che fallisce
  `validate_adapter_manifest()`, e rifiuta due file che dichiarano lo
  stesso `adapterId`. `catalog_server.py` non ha nessun
  `do_POST`/`do_PUT` da nessuna parte - un tentativo di scrittura riceve
  il proprio `501` onesto di `BaseHTTPRequestHandler`, mai una rotta che
  questo progetto ha dimenticato di proteggere.
- **Il cancello di sicurezza riusa la vera logica di HYDRA-UMC-SDK, mai
  una seconda implementazione di essa.** Il
  `evaluate_capability_call()` di `sdk_gate.py` chiama direttamente
  `hydra_umc_sdk.bridge_contract.evaluate_job()` per ogni capacità
  `write`/`abort` - una capacità `read` non tocca mai l'SDK, poiché
  `evaluate_job()` è un cancello di movimento/scrittura, non un cancello
  di lettura. Vedi [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)
  per l'unica semplificazione deliberata e nominata che fa questa
  integrazione (un `JobPhase` sostitutivo unico per qualsiasi scrittura
  che non sia un abort).
- **Un registro di certificazione è onesto su cosa può e non può
  provare.** `certification.py` rifiuta di salvare una certificazione la
  cui evidenza non corrisponde all'`evidenceSchema` dell'adattatore, ma
  non afferma mai di verificare in modo indipendente che quell'evidenza
  provenga da hardware reale - non esiste in nessuna parte di questo
  progetto un percorso di codice che apra una vera porta seriale/sessione
  OPC-UA/connessione MQTT per verificarlo. Vedi
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Le dieci fixture nominano veri progetti proprietari, mai
  inventati.** Ogni `ownerProject` in `fixtures/*.json` è un vero
  repository di questo ecosistema (vedi la sezione Progetti Correlati) -
  questo è un vero modello di registro, non uno speculativo.
- **Solo libreria standard per il nucleo.**
  `validate`/`catalog`/`serve-catalog`/`certify`/`certifications` non
  richiedono alcuna dipendenza - `json`, Python semplice per i controlli
  strutturali, e `http.server`. Solo `gate` su una capacità
  `write`/`abort` richiede l'extra opzionale `[sdk]`.

## 🔒 Sicurezza e protezione

| Minaccia | Difesa | Dove |
|---|---|---|
| Un adattatore che si spaccia per un altro progetto | Il progetto proprietario deve rispettare `^(HYDRA-UMC\|URTC)(-[A-Z0-9-]+)?$` e con `--ecosystem-root` viene controllato contro il `hydra-umc.project.json` di quel repository | `schema.py`, `cli.py` |
| Credenziali in un manifesto, un manifesto enorme, una modalità sconosciuta | `authenticationRef` accetta solo i prefissi `env:`, `secret-store:`, `vault:` o `none:` (mai il segreto stesso); un manifesto è al massimo 1 000 000 byte; le modalità di capacità sono `read`, `write` e `abort`, l'idempotenza è `none`, `idempotent`, `at-least-once` o `exactly-once` | `schema.py` |
| Chiamare un adattatore senza la porta, una richiesta vecchia | `gate` chiama l'`evaluate_job()` proprio dell'SDK e mai una seconda implementazione; richiede `--allow-unobserved` per fidarsi di uno stato dichiarato, e `--human-confirmed`, `--safety-gate` e `--permission` come chiede il manifesto; una richiesta più vecchia di 30 secondi o in anticipo di oltre 5 secondi viene rifiutata | `sdk_gate.py`, `cli.py` |
| Registri di certificazione manomessi e una scrittura via rete | I registri formano una catena di hash sigillata con una chiave di almeno 16 caratteri (`.chain-head.json`, `.chain.lock`) e `verify --strict` fallisce davanti a un registro fuori dalla catena; `catalog` e `serve-catalog` sono solo GET: nel progetto non esiste alcun percorso di scrittura via rete | `ledger.py`, `catalog_server.py` |

**Cosa non fa mai:** non tocca mai una macchina, e una certificazione conserva ciò che una persona attesta: la prova non viene verificata contro hardware reale (vedi `docs/CERTIFICATION.md`).

## 🔌 Interfacce

Il comando `hydra-umc-connector-hub` (o `./run.sh`); il riferimento completo è `docs/CLI_REFERENCE.md`. Il catalogo è servito anche via HTTP, solo GET, su `127.0.0.1:8801` per impostazione predefinita.

| Topic o rotta | Cosa porta |
|---|---|
| `validate MANIFEST...` | controllare i manifesti contro il contratto |
| `catalog --registry-dir DIR`, `serve-catalog --registry-dir DIR --port 8801` | elencare gli adattatori, o servire lo stesso elenco via GET (`--ecosystem-root` controlla anche i progetti proprietari) |
| `gate MANIFEST --capability ... --job-id ... --idempotency-key ... --source ... --cell-state ... --machine-state ...` | far passare una capacità dalla porta dell'SDK (`--param k=v`, `--evidence-file`, `--allow-unobserved`, `--human-confirmed`, `--safety-gate`, `--permission`) |
| `certify`, `certifications`, `verify --strict` | registrare l'attestazione di una persona nella catena di hash, elencare i registri, verificare la catena |

## ⚙️ Configurazione

Non ci sono variabili d'ambiente proprie: la cartella del registro, host e porta del catalogo (`--registry-dir`, `--host`, `--port`) e la chiave della catena di certificazione (almeno 16 caratteri) sono argomenti della riga di comando. Le credenziali di un adattatore non si scrivono mai nel suo manifesto, solo un riferimento a dove si trovano.

## 🚀 Avvio rapido

Richiede Python 3.11 o successivo; il nucleo usa solo la libreria standard (l'extra `sdk`, `pip install -e ".[sdk]"`, serve solo per `gate` su una capacità di scrittura o interruzione).

```bash
chmod +x build.sh   # una tantum
./build.sh          # crea .venv, pip install -e ".[dev]", compile-check + test
./run.sh                                   # demo reale: valida le dieci fixture reali
./run.sh validate fixtures/industrial-opcua.json
./run.sh validate fixtures/invalid/*.json  # ognuna di queste dovrebbe riportare INVALID
./run.sh catalog --registry-dir fixtures
./run.sh serve-catalog --registry-dir fixtures --port 8801   # Ctrl+C per fermare
pip install -e ".[sdk]"                    # necessario solo per `gate` su una capacità write/abort
./run.sh gate fixtures/cnc-grbl.json --capability sendControlByte --job-id j1 \
    --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
./run.sh certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Il Tuo Nome" --evidence-file real-status.json --out-dir certifications/
```

Su Windows: `build.bat`, poi `run.bat` (stessa demo se chiamato senza
argomenti) / uno qualsiasi dei sottocomandi sopra. `build-test.sh`/`.bat`
esegue lo stesso controllo di compilazione (solo sintassi Python),
senza modificare nulla, che la propria CI di questo progetto esegue -
NON esegue da solo la suite di test; la CI esegue `pytest` come passo
separato, successivo. Esegui `./build.sh`/`build.bat` (o `pytest
tests/` direttamente) per la suite di test locale completa.

**Risoluzione dei problemi**

- `validate` riporta `INVALID` per un manifesto che credi corretto:
  leggi ogni motivo elencato - il validatore li riporta tutti, non solo
  il primo. Vedi [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)
  per il contratto esatto campo per campo.
- `validate` riporta `ERROR: ... is not valid JSON`: il file stesso è
  JSON malformato, distinto da un manifesto ben formato ma invalido -
  controlla una virgola o virgoletta mancante prima di controllare il
  contratto stesso.
- `catalog`/`serve-catalog` termina con codice `1` o elenca un file
  sotto `invalidFiles`: quel file ha fallito la validazione strutturale
  ed è stato deliberatamente lasciato fuori dal catalogo - esegui
  `validate` direttamente su di esso per l'elenco completo dei motivi.
- `gate` fallisce con `ERROR: the optional 'hydra-umc-sdk' package is
  not installed`: esegui prima `pip install -e ".[sdk]"` - necessario
  solo per una capacità `write`/`abort`.
- `gate`/`certify` fallisce con `ERROR: unknown cell_state ...` oppure
  `... does not match evidenceSchema`: vedi
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)/
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md) per i valori/forme
  esatti attesi.

## 🧪 Test

188 test automatici si eseguono con `python -m pytest -q tests` (39 richiedono l'extra `sdk` e vengono saltati senza): lo schema e il JSON Schema pubblicato, il catalogo, la porta dell'SDK, la catena di certificazione, la riga di comando e input ostili. Né hardware né rete esterna.

La CI esegue `HYDRA_UMC_CI=1 python tools/ci_validate.py`, che controlla il manifesto, i documenti, gli otto README e le immagini.

## 🏗️ Compilazione e rilascio

Per un rilascio non c'è nulla da compilare: `build.sh` / `build.bat` creano l'ambiente virtuale, installano il pacchetto in modalità modificabile ed eseguono i test, e `build-test` si limita a controllare. Compilare non cambia mai la versione; la alza soltanto `python tools/hydra_project_tool.py bump`, che sposta anche il registro delle modifiche. La versione del pacchetto, del manifesto e del registro deve coincidere, altrimenti `ci_validate.py` fallisce.

## 🩺 Risoluzione dei problemi

| Vedi | Perché | Fai |
|---|---|---|
| `INVALID` on a manifest | Il manifesto viola il contratto: un progetto proprietario sbagliato, un segreto in `authenticationRef`, una modalità sconosciuta o più di 1 000 000 byte | Leggi il messaggio di `validate`; `./run.sh validate fixtures/invalid/*.json` mostra ogni tipo di errore |
| `gate` refuses a write or abort capability | L'SDK non è installato, o lo stato non è stato osservato, o manca una conferma richiesta dal manifesto | `pip install -e ".[sdk]"`; dai `--observed-machine-state`, o `--allow-unobserved` se accetti lo stato dichiarato; aggiungi `--human-confirmed`, `--safety-gate` e `--permission` come richiesto |
| `verify --strict` fails | Un registro di certificazione è fuori dalla catena di hash o la chiave è sbagliata | Usa la chiave con cui è stata sigillata la catena (almeno 16 caratteri); un registro aggiunto o modificato a mano è fuori dalla catena per progetto |

## 📂 Struttura del repository

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-CONNECTOR-HUB" width="100%">
</p>

<details>
<summary>Versione testuale dell'albero</summary>

```text
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py                                il contratto del manifesto di adattatore e il suo validatore
│   ├── registry.py                              registra i veri bridge come adattatori
│   ├── catalog_server.py                        l'endpoint del catalogo solo GET
│   ├── sdk_gate.py                              chiama l'evaluate_job() proprio dell'SDK
│   ├── certification.py ledger.py               registri di certificazione in una catena di hash sigillata
│   └── cli.py                                   validate, catalog, serve-catalog, gate, certify
├── tests/                                       188 test
├── docs/                                        guide su manifesto, porta, certificazione e maturità
├── fixtures/                                    dieci veri manifesti di adattatore e quelli non validi
├── schemas/                                     il JSON Schema pubblicato
├── tools/                                       esecutore di build e test, aumento di versione, validatore CI, generatori e controlli di README e immagini
├── images/                                      banner e immagini del README
├── .github/                                     workflow CI e modelli di segnalazione
├── pyproject.toml                               metadati del pacchetto e dipendenze
├── hydra-umc.project.json                       manifesto: versione, maturità, famiglia
├── CHANGELOG.md                                 cosa è cambiato in ogni versione
├── build.sh build.bat                           script di build (non cambiano mai la versione)
├── build-test.sh build-test.bat                 script di build (non cambiano mai la versione)
├── test.sh test.bat                             eseguono i test
├── bump_version.py / bump_manifest_version.py   aumento di versione esplicito
├── run.sh run.bat                               la dimostrazione e i comandi
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE LICENSE.md
```

</details>

## 🗺️ Roadmap e limiti noti

**Limiti noti oggi**

Tutte e quattro le consegne del piano nominato nel proprio manifesto e
CHANGELOG di questo progetto spediscono ora codice reale e testato. Ciò
che resta, detto onestamente:

- **La lacuna di verifica hardware della Consegna 4 resta aperta
  deliberatamente.** `certify` registra un'evidenza attestata da un
  umano, verificata contro l'`evidenceSchema` proprio di un adattatore,
  ma nulla in questo progetto conferma in modo indipendente che
  quell'evidenza provenga davvero dalla macchina nominata - ciò richiede
  l'hardware fisico stesso, in una cella reale, che questa macchina di
  sviluppo non possiede. Vedi
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Integrazione con un vero client: iniziata, non finita.**
  HYDRA-UMC-SERVER ora interroga davvero `serve-catalog` -
  `GET /api/adapters` e `GET /api/adapters/:adapterId` inoltrano il vero
  catalogo di questo progetto, end-to-end (vedi il proprio
  `tools/verify_connector_hub_relay_contract.mjs` di HYDRA-UMC-SERVER,
  che avvia il vero `serve-catalog` di questo progetto contro i suoi
  veri `fixtures/` e una vera istanza di Server, mai un mock). È stato
  anche installato come un vero wheel in un venv al di fuori del proprio
  checkout di questo progetto ed eseguito da lì, confermando che il
  packaging stesso (non solo un'installazione editabile) funziona. Che
  Studio/Suite/Updater chiamino `gate` da soli resta un vero lavoro
  futuro, separato.
- **Manca un vero trasporto tra chi chiama `gate`/`certify` e lo stato
  reale della cella/macchina.** Oggi, `--cell-state`/`--machine-state`
  sono forniti da chi chiama come valori già noti - non esiste qui
  nessun percorso di codice che li recuperi dal vivo da
  HYDRA-UMC-SERVER o da un servizio di zone di sicurezza.

## 🌍 Lingue

Questo README e i documenti del repository esistono in otto lingue: inglese, spagnolo, tedesco, francese, italiano, giapponese, cinese e portoghese (Portogallo). Sono scritti insieme e la CI verifica che gli otto file abbiano le stesse sezioni e gli stessi link. Questo repository non ha uno schermo né un catalogo di messaggi propri, quindi non ci sono stringhe di interfaccia da tradurre.

## 🔗 Progetti correlati

Questo progetto fa parte dell'ecosistema robotico HYDRA-UMC dello stesso autore (JuanenRac / Electro Hobby 3D). Vale la pena conoscerlo, poiché una richiesta potrebbe in realtà riguardare uno di questi invece di questo repository.

**Direttamente Correlati**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — il contratto JSON-Schema condiviso contro cui ogni bridge valida già i propri comandi; il comando `gate` di questo hub (Consegna 3) chiama direttamente il proprio `bridge_contract.evaluate_job()` reale per una capacità write/abort, mai una seconda implementazione di quel cancello.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — un nuovo progetto affine: gestisce il ciclo di vita degli incidenti di manutenzione dei propri componenti di questo ecosistema, mentre questo hub scopre e valida cosa può fare una macchina/adattatore ESTERNO.
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — esplicitamente NON sostituito da questo progetto: GATEWAY-INDUSTRIAL è un vero relè di protocollo con la propria allowlist di comandi; questo hub è un registro/validatore dichiarativo che si colloca sopra di esso e sopra ogni altro bridge, mai una seconda implementazione di un protocollo.

**Fa Anche Parte dell'Ecosistema**

*Hardware e Piattaforma di Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — il progetto della scheda madre del braccio robotico: host CM5 + coprocessore STM32H745 dual-core, pensato per coordinare fino a 8 bracci utensile via CAN-OTA/SPI-OTA (firmware in fase iniziale; nessuna scheda assemblata per ora).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — livello prodotto riproducibile su Raspberry Pi OS per il CM5: agente in sola lettura, config/profili validati, provisioning WiFi al primo contatto.

*Backend Centrale e Client*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — il vero backend headless (REST/WebSocket) con cui parla davvero ogni client di controllo.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — dashboard di controllo web con visualizzazione 3D multi-robot in tempo reale.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro di comando sciame desktop (PySide6) per più server contemporaneamente.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo nativa per Android con login biometrico e un companion Wear OS abbinato.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo per iOS/iPadOS (Flutter) con sincronizzazione WebSocket in tempo reale.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaccia touch nativa per il touchscreen DSI da 7" a bordo, incorporata direttamente nel CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creatore/editor grafico desktop di URDF che invia i modelli finiti al catalogo di STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor desktop di modelli STL, che trasforma/sostituisce/rimuove/aggiunge veri pezzi nello stesso catalogo di modelli modificato anche da HYDRA-UMC-EDITOR-URDF.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barriera di coordinamento per flotte AGV/AMR tramite un publisher MQTT VDA 5050 (testato solo contro una flotta emulata); il vero `ownerProject` dietro la propria fixture `mobile-vda5050` di questo hub.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinatore ad alto livello per celle CNC con accesso a stato/byte di controllo GRBL (testato solo contro un emulatore); dietro la propria fixture `cnc-grbl` di questo hub.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barriera di coordinamento per droidi con zampe/umanoidi, con un mittente di comandi per Boston Dynamics Spot (testato solo contro un emulatore).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinatore per celle laser che legge 3 segnali GPIO di chiave/involucro/interblocco (testato solo contro un chip simulato; non può armare né far partire un laser); dietro la propria fixture `laser-safety` di questo hub.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinatore ad alto livello sicuro per il flusso schede del pick-and-place OpenPnP; dietro la propria fixture `pnp-openpnp` di questo hub.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — barriera di coordinamento sicura per stampanti 3D Moonraker/Klipper, con comandi di lavoro reali e controllati; dietro la propria fixture `printer-moonraker` di questo hub.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinatore con un trasporto ROS 2 rclpy importato in modo lazy (non ancora eseguito contro un'installazione ROS 2); dietro la propria fixture `robotics-ros2` di questo hub.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barriera di coordinamento per UAV dotati di fotocamera, con un mittente di comandi MAVLink (testato solo contro un emulatore); dietro la propria fixture `uav-mavlink` di questo hub.

*Piattaforma Strumenti URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware per la scheda fisica dell'Universal Robot Tool Controller, oltre 25 profili utensile su bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop con GUI per il flashing delle schede URTC, CAN-OTA più SWD/JTAG a chip intero.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica CAN-bus dal vivo per schede URTC, un pannello per profilo utensile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basata su browser a URTC-TESTER tramite la Web Serial API, senza installazione locale.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway davanti al bus CAN di URTC: elenco di identificatori consentiti, limite di frequenza e chiave di sessione; software provato su computer, non ancora su un bus reale.

*Nodo IA Visione (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub di integrazione per la pipeline di visione Hailo-8, con un vero controllo di prontezza hardware per fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro reale di modelli compilati con verifica di caricamento sicuro per architettura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generatore reale di pipeline GStreamer + config MediaMTX, con una vera barriera di integrazione HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — legge di correzione Position-Based Visual Servoing con autorizzazione condizionata allo stato di zona; ancora nessuna stima di posa da telecamera.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — logica v0 di violazione zona, freschezza di calibrazione e richiesta E-STOP che legge le posizioni degli oggetti da un file; nessun rilevatore la alimenta e nessun E-STOP fisico è ancora collegato.

*Nodo IA Cognitivo (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub di integrazione per la pipeline cognitiva Hailo-10 (orchestrazione LLM/VLA/voce).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vera codifica/decodifica di token d'azione e generazione di traiettoria per un modello Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vero front-end vocale (VAD + parser di intenti) con un relay verso Watch limitato e soggetto a conferma.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vera scomposizione dei task basata su regole e recupero semantico degli errori sui codici errore MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vera ricerca documentale TF-IDF (solo libreria standard) sui documenti Markdown di questo ecosistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — tecnico di manutenzione IA locale e con cancelli di policy per l'ecosistema stesso - osserva, diagnostica e propone correzioni; i due livelli di rischio più alti non sono deliberatamente ancora implementati.

*Orchestrazione e Sciame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub di integrazione con un vero contratto di health-report gRPC/Protobuf e una macchina a stati di missione.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vera coda di lavori basata su priorità con deduplicazione, su una vera API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vero watchdog di salute della flotta basato su gRPC, con retry/backoff e rilevamento di discrepanza d'identità.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vero pianificatore di percorsi 3D basato su RRT, con vera validazione delle collisioni ostacolo/spazio di lavoro.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vera sincronizzazione di stato CRDT LWW-Element-Map, con property test per la convergenza multi-cella.

*Gemello Digitale e Simulazione*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub di integrazione per il motore di gemello digitale, con un vero contratto di sincronizzazione per compatibilità di versione.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — router hardware-in-the-loop con un interblocco software di collisione tra simulazione e hardware reale (testato senza hardware reale).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vera cinematica diretta e validazione dei limiti articolari su un vero sottoinsieme URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vero generatore procedurale di scene 2D con esportazione di annotazioni YOLO/COCO.

*Dati e Analisi*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vero archivio di serie temporali basato su sqlite3, con una vera API HTTP di ingestione/query.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vero rilevatore di anomalie FFT + baseline statistica, con monitoraggio della deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vero calcolo OEE/disponibilità sullo storico di DATALAKE, con esportazione CSV riproducibile.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vera pipeline di ingestione CAN/WebSocket verso DATALAKE, con deduplicazione per sequenza.

*Gateway Industriale*
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vero spazio di indirizzi OPC-UA, verificato con una vera sessione client del protocollo binario; il vero `ownerProject` dietro la propria fixture `industrial-opcua` di questo hub.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vero broker MQTT con autenticazione opzionale per client e ACL sui topic; dietro la propria fixture `industrial-mqtt` di questo hub.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — veri endpoint XML `/probe` e `/current` di MTConnect, con output in modalità degradata; dietro la propria fixture `manufacturing-mtconnect` di questo hub.

*Operazioni dell'Ecosistema*
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — rileva, installa e aggiorna ogni checkout dell'ecosistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — costruisce un'immagine CM5 nuova e completamente aggiornata.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — host di sviluppo riproducibile (Raspberry Pi 5 / CM5) che conserva il codice sorgente dell'ecosistema ed esegue attività delimitate di build/test tramite una coda durevole; un ruolo di sviluppo dedicato, esplicitamente distinto da un CM5 operativo.
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — pannelli Smart Summaries e Anomaly Highlighting su DATALAKE/ANOMALY-DETECTOR, con un fallback statistico onesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI di flotta con un vero e stabile contratto di exit-code, un client live reale della stessa API di HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app companion WearOS con schemi di avviso aptico e un relay vocale verso il telefono abbinato (non ancora eseguita su un orologio fisico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware per un rack di montaggio schede con decodifica reale dell'ID utensile e logica di preriscaldamento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware più un vero companion di visione Python per una testa utensile di ispezione termica/RGB.

## 📚 Documentazione

Dove leggere di più:

* [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md) - il contratto del manifesto di adattatore campo per campo
* [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) - come una capacità attraversa la porta dell'SDK
* [docs/CERTIFICATION.md](docs/CERTIFICATION.md) - cos'è e cosa non è un registro di certificazione
* [docs/MATURITY_CRITERIA.md](docs/MATURITY_CRITERIA.md) - quando un adattatore conta come più maturo
* [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) - ogni comando e opzione, con output reale catturato
* [Base di sicurezza dell'ecosistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Modello delle minacce dell'ecosistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Registro delle modifiche di questo repository](CHANGELOG.md)
* [Licenza di questo repository](LICENSE.md)

## 🤝 Contribuire e comunità

* Prima di una pull request esegui `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (oppure `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): deve stampare `CI_VALIDATION=PASS`. Non eseguire `build.sh` né `build.bat` per questa verifica; compilare non è verificare.
* I otto README sono scritti da un'unica fonte in HYDRA-UMC-DOCS; non modificarli a mano. Cambia la fonte e riscrivili con `tools/make_readmes.py`.
* Non affermare in un README ciò che non è stato eseguito: scrivi «simulato» o «non provato su hardware» quando è la verità.
* Vedi [CONTRIBUTING.md](CONTRIBUTING.md), il [codice di condotta](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) e [SUPPORT.md](SUPPORT.md).

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - [LICENSE](LICENSE).
