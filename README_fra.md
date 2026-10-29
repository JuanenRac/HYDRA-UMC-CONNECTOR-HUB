<!-- =============================================================================
HYDRA-UMC-CONNECTOR-HUB - Adapter-manifest registry
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | 🇫🇷 <b>Français</b> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🧩 Un registre déclaratif et un validateur pour les adaptateurs de machines externes

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

> **État : v0.1.5, functional - Livraisons 1-4 sur 4 (schéma/CLI/
> fixtures, catalogue en lecture seule, barrière de sécurité SDK,
> registres de certification).** `catalog`/`serve-catalog` sont réels et
> uniquement GET (aucune route d'écriture réseau n'existe nulle part
> dans ce projet) ; `gate` appelle directement le propre `evaluate_job()`
> réel de HYDRA-UMC-SDK, jamais une seconde implémentation de cette
> barrière (voir
> [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)) ; `certify`
> enregistre une preuve réelle attestée par un humain mais ne la vérifie
> explicitement PAS de façon indépendante contre du matériel réel - voir
> [docs/CERTIFICATION.md](docs/CERTIFICATION.md) pour comprendre
> exactement pourquoi cela reste hors périmètre sans machine physique en
> main. Voir [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) pour la
> surface de commandes exacte qui existe aujourd'hui.

> **Vérification d'honnêteté - ce qui fonctionne réellement aujourd'hui :** le schéma/validateur de manifeste (`schema.py`), le catalogue en lecture seule (`registry.py`, `catalog_server.py`), l'intégration de la porte de sécurité du SDK (`sdk_gate.py`, appelant le propre `evaluate_job()` réel de `HYDRA-UMC-SDK` sur un checkout réellement installé, jamais une simulation), le journal de certification (`certification.py`), et la CLI (`cli.py`) sont réels et couverts par 188 tests qui passent (`pytest tests/`, avec l'extra optionnel `[sdk]` installé - 34 sont ignorés sans lui). `certify` enregistre une évidence attestée par un humain mais ne la vérifie explicitement pas de façon indépendante contre du matériel réel - il n'y a aucune machine physique derrière aucune des 10 fixtures, et aucun adaptateur ici n'a jamais été utilisé pour réellement parler à un vrai appareil. `catalog`/`serve-catalog` sont GET-only par construction (`catalog_server.py` n'a aucun `do_POST`/`do_PUT`). Voir l'encart Statut ci-dessus et `CHANGELOG.md` pour ce qui a été exactement livré jusqu'à présent.

> **État de la sûreté et de la cybersécurité :** cet écosystème n'est pas un système de sécurité certifié. Il n'existe pas encore de chaîne d'E-STOP matérielle, ni de limites ou de verrouillages imposés par le firmware, ni de commande de mouvement vérifiée ; les images de firmware sont contrôlées par CRC32 et un HMAC-SHA256 à clé partagée, pas par une signature asymétrique ; TLS et TLS mutuel sont optionnels et désactivés par défaut ; aucune carte propre n'a encore été assemblée ni testée. Lisez la [base de sécurité](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) et le [modèle de menaces](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) avant de vous fier à une affirmation d'ici pour la sécurité d'une personne.

---

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.1.5` |
| Maturité | Fonctionnel |
| Tests | 188 (`python -m pytest -q tests`) |
| Technologie | Python 3.11+ / JSON Schema (hand-written structural validator, no jsonschema dependency) / http.server (stdlib-only real read-only catalog endpoint) / HYDRA-UMC-SDK (optional, real safety-gate integration via evaluate_job()) |
| Cible | Le PC de la personne qui l'utilise |
| Sur matériel réel | Pas encore : aucune exécution sur du matériel réel n'est consignée pour cette version |

**Aller à :** [Présentation](#-présentation) · [Architecture](#-architecture) · [Sécurité et protection](#-sécurité-et-protection) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Démarrage rapide](#-démarrage-rapide) · [Tests](#-tests) · [Dépannage](#-dépannage) · [Structure du dépôt](#-structure-du-dépôt) · [Projets liés](#-projets-liés)

## 🚦 État du projet

Chaque ligne est une partie de ce dépôt et le feu dit où elle en est aujourd'hui. Elle est écrite d'après ce que le dépôt peut montrer (tests, compilations, exécutions), pas d'après ce qui est prévu.

🟢 Fait et vérifié · 🟡 Fonctionne, avec des limites connues · 🟠 À moitié fait ou pas encore vérifié · 🔴 Pas fait ou ne fonctionne pas

| Domaine | État | Ce que cela veut dire ici |
|---|---|---|
| Logiciel | 🟡 | Fonctionne pour son usage principal ; la vérification d'honnêteté ci-dessus liste ce qui manque encore |
| Tests | 🟢 | 188 tests automatiques, exécutés à chaque modification |
| Matériel réel | 🔴 | Pas encore : aucune exécution sur du matériel réel n'est consignée pour cette version |
| Documentation | 🟢 | README en huit langues, vérifié par rapport au manifeste à chaque modification |

## 🎯 Présentation

Aujourd'hui, choisir et configurer quel bridge utilise une cellule/
machine donnée est réparti entre des README, des fichiers `.env` et des
scripts ad hoc dans de nombreux dépôts de bridges réels.
HYDRA-UMC-CONNECTOR-HUB est destiné à devenir l'unique endroit qui
répond, pour toute machine externe réelle, à trois questions : **quel
protocole parle-t-elle, que peut-elle vraiment faire (lire/écrire/
avorter, avec quel risque), et quel projet réel déjà existant de cet
écosystème l'implémente déjà ?**

Cette version expédie les quatre livraisons prévues, en six parties :

1. **Un contrat réel et fixe** ([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)) -
   le "CONTRATO MINIMO DE ADAPTADOR" de cet écosystème,
   avec une règle non négociable déjà appliquée en code : une capacité
   `write`/`abort` est rejetée à moins qu'elle ne déclare aussi son
   propre risque, la permission requise, l'état de cellule requis,
   l'exigence de confirmation humaine et le délai d'expiration.
2. **Un vrai validateur CLI** (`hydra-umc-connector-hub validate`) - une
   vérification structurelle écrite à la main (sans dépendance
   `jsonschema`), afin que chaque erreur réelle nomme exactement
   l'adaptateur/champ/capacité en cause.
3. **Dix vraies fixtures**, une par projet de bridge/protocole déjà
   existant dans cet écosystème - la preuve que le contrat n'est pas
   théorique, et un modèle de départ pour un nouveau manifeste
   d'adaptateur.
4. **Un vrai catalogue en lecture seule** (`catalog`/`serve-catalog`) -
   découvre chaque manifeste structurellement valide d'un répertoire et,
   avec `serve-catalog`, l'expose via un vrai `http.server` uniquement
   GET (aucune route d'écriture n'existe nulle part dans ce projet).
5. **Une vraie intégration avec la barrière de sécurité de
   HYDRA-UMC-SDK** (`gate`) - un appel de capacité `write`/`abort` est
   arbitré par le propre `evaluate_job()` réel du SDK, jamais une
   seconde implémentation de cette logique ; voir
   [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md).
6. **De vrais registres de certification** (`certify`/`certifications`)
   - un journal réel, attesté par un humain et uniquement en ajout,
   vérifié contre le propre `evidenceSchema` d'un adaptateur ; voir
   [docs/CERTIFICATION.md](docs/CERTIFICATION.md) pour comprendre
   pourquoi vérifier la preuve de façon indépendante contre du matériel
   réel reste explicitement hors périmètre ici.

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

Il n'existe ni invocation par défaut/sans argument ni GUI nulle part
dans ce projet - voir [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)
pour la surface de commandes complète et réelle.

## 🧩 Rôle dans HYDRA-UMC

**HYDRA-UMC-CONNECTOR-HUB** décrit comment des machines extérieures se raccordent à l'écosystème, sans se connecter à aucune. Un adaptateur dit dans un manifeste ce qu'il est, ce qu'il sait faire (lire, écrire, abandonner) et comment il s'authentifie ; le hub le valide, le liste, fait passer une capacité demandée par la vraie porte du SDK et garde trace de qui a certifié quoi.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-CONNECTOR-HUB architecture" width="100%">
</p>

**Pourquoi il est construit ainsi**

- **Un validateur écrit à la main, pas `jsonschema`.** Le propre
  contrat de la Livraison 1 est assez petit (14 champs de premier
  niveau, une forme de capacité imbriquée) pour qu'une simple fonction
  Python collectant des chaînes d'erreur réelles et spécifiques soit à
  la fois plus simple qu'un validateur JSON-Schema générique ET
  produise une sortie plus claire - chaque message nomme exactement le
  champ/index en cause, pas un chemin de schéma générique.
- **La règle de sécurité write/abort est appliquée en code, pas en
  documentation.** `_WRITE_CAPABILITY_REQUIRED_FIELDS` dans `schema.py`
  est cette règle explicite transformée en une
  vérification réelle et testée - l'auteur d'un manifeste ne peut pas
  l'oublier, car le validateur rejette une capacité qui le fait.
- **`authenticationRef` est vérifié comme une référence, jamais accepté
  comme texte libre.** Un ensemble fermé de vrais préfixes (`env:`,
  `secret-store:`, `vault:`, `none:`) - délibérément pas une heuristique
  "ressemble à un secret" (voir le propre `log_redaction.py` de
  HYDRA-UMC-OPS-AGENT pour comprendre pourquoi une heuristique est le
  mauvais outil ici aussi pour exactement ce même problème).
- **Chaque erreur est collectée, jamais seulement la première.**
  `validate_adapter_manifest()` continue de vérifier après avoir trouvé
  un problème - une personne corrigeant un manifeste voit tous les
  vrais problèmes en une seule exécution.
- **Le catalogue est réel et en lecture seule, délibérément.**
  `registry.py` scanne un répertoire sans récursion (une
  `fixtures/invalid/` imbriquée ne rejoint donc jamais un vrai
  catalogue), écarte - mais continue de rapporter - tout ce qui échoue à
  `validate_adapter_manifest()`, et rejette deux fichiers déclarant le
  même `adapterId`. `catalog_server.py` n'a aucun `do_POST`/`do_PUT`
  nulle part - une tentative d'écriture reçoit le propre `501` honnête
  de `BaseHTTPRequestHandler`, jamais une route que ce projet aurait
  oublié de protéger.
- **La barrière de sécurité réutilise la vraie logique de
  HYDRA-UMC-SDK, jamais une seconde implémentation de celle-ci.** Le
  `evaluate_capability_call()` de `sdk_gate.py` appelle directement
  `hydra_umc_sdk.bridge_contract.evaluate_job()` pour chaque capacité
  `write`/`abort` - une capacité `read` ne touche jamais le SDK, car
  `evaluate_job()` est une barrière de mouvement/écriture, pas une
  barrière de lecture. Voir
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) pour l'unique
  simplification délibérée et nommée que fait cette intégration (un
  `JobPhase` de remplacement unique pour toute écriture qui n'est pas un
  abort).
- **Un registre de certification est honnête sur ce qu'il peut et ne
  peut pas prouver.** `certification.py` refuse d'enregistrer une
  certification dont la preuve ne correspond pas à l'`evidenceSchema` de
  l'adaptateur, mais n'affirme jamais vérifier de façon indépendante que
  cette preuve provient de matériel réel - il n'existe nulle part dans
  ce projet de chemin de code ouvrant un vrai port série/une vraie
  session OPC-UA/une vraie connexion MQTT pour le vérifier. Voir
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Les dix fixtures nomment de vrais projets propriétaires, jamais
  inventés.** Chaque `ownerProject` dans `fixtures/*.json` est un vrai
  dépôt de cet écosystème (voir la section Projets Liés) - c'est un vrai
  modèle de registre, pas un modèle spéculatif.
- **Bibliothèque standard uniquement pour le cœur.**
  `validate`/`catalog`/`serve-catalog`/`certify`/`certifications` ne
  nécessitent aucune dépendance - `json`, du Python simple pour les
  vérifications structurelles, et `http.server`. Seul `gate` sur une
  capacité `write`/`abort` nécessite l'extra optionnel `[sdk]`.

## 🔒 Sécurité et protection

| Menace | Défense | Où |
|---|---|---|
| Un adaptateur qui se fait passer pour un autre projet | Le projet propriétaire doit respecter `^(HYDRA-UMC\|URTC)(-[A-Z0-9-]+)?$` et, avec `--ecosystem-root`, il est contrôlé contre le `hydra-umc.project.json` de ce dépôt | `schema.py`, `cli.py` |
| Des identifiants dans un manifeste, un manifeste énorme, un mode inconnu | `authenticationRef` n'accepte que les préfixes `env:`, `secret-store:`, `vault:` ou `none:` (jamais le secret lui-même) ; un manifeste fait 1 000 000 octets au plus ; les modes de capacité sont `read`, `write` et `abort`, l'idempotence est `none`, `idempotent`, `at-least-once` ou `exactly-once` | `schema.py` |
| Appeler un adaptateur sans la porte, une requête ancienne | `gate` appelle le `evaluate_job()` propre du SDK et jamais une seconde implémentation ; il exige `--allow-unobserved` pour croire un état déclaré, et `--human-confirmed`, `--safety-gate` et `--permission` selon le manifeste ; une requête de plus de 30 secondes ou en avance de plus de 5 secondes est refusée | `sdk_gate.py`, `cli.py` |
| Des enregistrements de certification altérés et une écriture par le réseau | Les enregistrements forment une chaîne de hachage scellée par une clé d'au moins 16 caractères (`.chain-head.json`, `.chain.lock`) et `verify --strict` échoue devant un enregistrement hors de la chaîne ; `catalog` et `serve-catalog` sont en GET seul : aucun chemin d'écriture par le réseau n'existe dans le projet | `ledger.py`, `catalog_server.py` |

**Ce qu'il ne fait jamais :** il ne touche jamais une machine, et une certification garde ce qu'une personne atteste : la preuve n'est pas vérifiée contre du matériel réel (voir `docs/CERTIFICATION.md`).

## 🔌 Interfaces

La commande `hydra-umc-connector-hub` (ou `./run.sh`) ; la référence complète est `docs/CLI_REFERENCE.md`. Le catalogue est aussi servi en HTTP, GET seul, sur `127.0.0.1:8801` par défaut.

| Topic ou route | Ce qu'il porte |
|---|---|
| `validate MANIFEST...` | contrôler des manifestes contre le contrat |
| `catalog --registry-dir DIR`, `serve-catalog --registry-dir DIR --port 8801` | lister les adaptateurs, ou servir la même liste en GET (`--ecosystem-root` contrôle aussi les projets propriétaires) |
| `gate MANIFEST --capability ... --job-id ... --idempotency-key ... --source ... --cell-state ... --machine-state ...` | faire passer une capacité par la porte du SDK (`--param k=v`, `--evidence-file`, `--allow-unobserved`, `--human-confirmed`, `--safety-gate`, `--permission`) |
| `certify`, `certifications`, `verify --strict` | enregistrer l'attestation d'une personne dans la chaîne de hachage, lister les enregistrements, vérifier la chaîne |

## ⚙️ Configuration

Il n'y a pas de variables d'environnement propres : le dossier du registre, l'hôte et le port du catalogue (`--registry-dir`, `--host`, `--port`) et la clé de la chaîne de certification (16 caractères au minimum) sont des arguments de la ligne de commande. Les identifiants d'un adaptateur ne sont jamais écrits dans son manifeste, seulement une référence à leur emplacement.

## 🚀 Démarrage rapide

Nécessite Python 3.11 ou plus récent ; le cœur n'utilise que la bibliothèque standard (l'extra `sdk`, `pip install -e ".[sdk]"`, n'est nécessaire que pour `gate` sur une capacité d'écriture ou d'abandon).

```bash
chmod +x build.sh   # une seule fois
./build.sh          # crée .venv, pip install -e ".[dev]", compile-check + tests
./run.sh                                   # démo réelle : valide les dix vraies fixtures
./run.sh validate fixtures/industrial-opcua.json
./run.sh validate fixtures/invalid/*.json  # chacune devrait rapporter INVALID
./run.sh catalog --registry-dir fixtures
./run.sh serve-catalog --registry-dir fixtures --port 8801   # Ctrl+C pour arrêter
pip install -e ".[sdk]"                    # nécessaire seulement pour `gate` sur une capacité write/abort
./run.sh gate fixtures/cnc-grbl.json --capability sendControlByte --job-id j1 \
    --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
./run.sh certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Votre Nom" --evidence-file real-status.json --out-dir certifications/
```

Sous Windows : `build.bat`, puis `run.bat` (même démo sans argument) /
n'importe laquelle des sous-commandes ci-dessus. `build-test.sh`/`.bat`
effectue la même vérification de compilation (syntaxe Python
uniquement), sans rien modifier, que la propre CI de ce projet
effectue - il n'exécute PAS la suite de tests lui-même; la CI exécute
`pytest` comme une étape séparée, ultérieure. Lancez
`./build.sh`/`build.bat` (ou `pytest tests/` directement) pour la
suite de tests locale complète.

**Dépannage**

- `validate` rapporte `INVALID` pour un manifeste que vous croyez
  correct : lisez chaque raison listée - le validateur les rapporte
  toutes, pas seulement la première. Voir
  [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md) pour le contrat
  exact champ par champ.
- `validate` rapporte `ERROR: ... is not valid JSON` : le fichier
  lui-même est un JSON malformé, distinct d'un manifeste bien formé mais
  invalide - vérifiez une virgule ou un guillemet manquant avant de
  vérifier le contrat lui-même.
- `catalog`/`serve-catalog` se termine avec le code `1` ou liste un
  fichier sous `invalidFiles` : ce fichier a échoué à la validation
  structurelle et a été délibérément laissé hors du catalogue - lancez
  `validate` directement dessus pour voir la liste complète des raisons.
- `gate` échoue avec `ERROR: the optional 'hydra-umc-sdk' package is not
  installed` : lancez d'abord `pip install -e ".[sdk]"` - nécessaire
  seulement pour une capacité `write`/`abort`.
- `gate`/`certify` échoue avec `ERROR: unknown cell_state ...` ou
  `... does not match evidenceSchema` : voir
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)/
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md) pour les valeurs/formes
  exactes attendues.

## 🧪 Tests

188 tests automatiques s'exécutent avec `python -m pytest -q tests` (39 d'entre eux exigent l'extra `sdk` et sont ignorés sans lui) : le schéma et le JSON Schema publié, le catalogue, la porte du SDK, la chaîne de certification, la ligne de commande et les entrées hostiles. Ni matériel ni réseau extérieur.

La CI exécute `HYDRA_UMC_CI=1 python tools/ci_validate.py`, qui vérifie le manifeste, les documents, les huit README et les images.

## 🏗️ Compilation et publication

Il n'y a rien à compiler pour une publication : `build.sh` / `build.bat` créent l'environnement virtuel, installent le paquet en mode éditable et lancent les tests, et `build-test` ne fait que vérifier. Construire ne change jamais la version ; seul `python tools/hydra_project_tool.py bump` la monte, et il fait avancer aussi le journal des modifications. La version du paquet, du manifeste et du journal doit concorder, sinon `ci_validate.py` échoue.

## 🩺 Dépannage

| Vous voyez | Parce que | Faites |
|---|---|---|
| `INVALID` on a manifest | Le manifeste viole le contrat : un mauvais projet propriétaire, un secret dans `authenticationRef`, un mode inconnu ou plus de 1 000 000 octets | Lisez le message de `validate` ; `./run.sh validate fixtures/invalid/*.json` montre chaque type d'échec |
| `gate` refuses a write or abort capability | Le SDK n'est pas installé, ou l'état n'a pas été observé, ou une confirmation exigée par le manifeste manque | `pip install -e ".[sdk]"` ; donnez `--observed-machine-state`, ou `--allow-unobserved` si vous acceptez l'état déclaré ; ajoutez `--human-confirmed`, `--safety-gate` et `--permission` selon la demande |
| `verify --strict` fails | Un enregistrement de certification est hors de la chaîne de hachage ou la clé est fausse | Utilisez la clé avec laquelle la chaîne a été scellée (16 caractères au minimum) ; un enregistrement ajouté ou modifié à la main est hors de la chaîne par construction |

## 📂 Structure du dépôt

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-CONNECTOR-HUB" width="100%">
</p>

<details>
<summary>Version texte de l'arborescence</summary>

```text
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py                                le contrat du manifeste d'adaptateur et son validateur
│   ├── registry.py                              enregistre les vrais bridges comme adaptateurs
│   ├── catalog_server.py                        le point d'accès du catalogue en GET seul
│   ├── sdk_gate.py                              appelle le evaluate_job() propre du SDK
│   ├── certification.py ledger.py               enregistrements de certification dans une chaîne de hachage scellée
│   └── cli.py                                   validate, catalog, serve-catalog, gate, certify
├── tests/                                       188 tests
├── docs/                                        guides du manifeste, de la porte, de la certification et de la maturité
├── fixtures/                                    dix vrais manifestes d'adaptateur et les invalides
├── schemas/                                     le JSON Schema publié
├── tools/                                       exécuteur de build et de tests, montée de version, validateur CI, générateurs et vérifications des README et des images
├── images/                                      bannière et images du README
├── .github/                                     workflow CI et modèles de tickets
├── pyproject.toml                               métadonnées du paquet et dépendances
├── hydra-umc.project.json                       manifeste : version, maturité, famille
├── CHANGELOG.md                                 ce qui a changé à chaque version
├── build.sh build.bat                           scripts de build (ils ne changent jamais la version)
├── build-test.sh build-test.bat                 scripts de build (ils ne changent jamais la version)
├── test.sh test.bat                             lancent les tests
├── bump_version.py / bump_manifest_version.py   montée de version explicite
├── run.sh run.bat                               la démonstration et les commandes
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE LICENSE.md
```

</details>

## 🗺️ Feuille de route et limites connues

**Limites connues aujourd'hui**

Les quatre livraisons du plan nommé dans le propre manifeste et
CHANGELOG de ce projet expédient maintenant du code réel et testé. Ce
qui reste, dit honnêtement :

- **Le manque de vérification matérielle de la Livraison 4 reste ouvert
  délibérément.** `certify` enregistre une preuve attestée par un
  humain, vérifiée contre l'`evidenceSchema` propre d'un adaptateur,
  mais rien dans ce projet ne confirme de façon indépendante que cette
  preuve provient réellement de la machine nommée - cela nécessite le
  matériel physique lui-même, dans une cellule réelle, que cette machine
  de développement n'a pas. Voir
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Intégration avec un vrai client : commencée, pas terminée.**
  HYDRA-UMC-SERVER sonde désormais réellement `serve-catalog` -
  `GET /api/adapters` et `GET /api/adapters/:adapterId` relaient le vrai
  catalogue de ce projet, de bout en bout (voir le propre
  `tools/verify_connector_hub_relay_contract.mjs` de HYDRA-UMC-SERVER,
  qui démarre le vrai `serve-catalog` de ce projet contre ses propres
  `fixtures/` réels et une vraie instance de Server, jamais un mock).
  Il a aussi été installé comme un vrai wheel dans un venv en dehors du
  propre checkout de ce projet et exécuté depuis là, confirmant que
  l'empaquetage lui-même (pas seulement une installation éditable)
  fonctionne. Que Studio/Suite/Updater appellent `gate` eux-mêmes reste
  un vrai travail futur, séparé.
- **Un vrai transport manque entre un appelant `gate`/`certify` et
  l'état réel de la cellule/machine.** Aujourd'hui, `--cell-state`/
  `--machine-state` sont fournis par l'appelant comme des valeurs déjà
  connues - il n'existe ici aucun chemin de code qui les récupère en
  direct depuis HYDRA-UMC-SERVER ou un service de zones de sécurité.

## 🌍 Langues

Ce README et les documents du dépôt existent en huit langues : anglais, espagnol, allemand, français, italien, japonais, chinois et portugais (Portugal). Ils sont écrits ensemble et la CI vérifie que les huit fichiers ont les mêmes sections et les mêmes liens. Ce dépôt n'a ni écran ni catalogue de messages propre, il n'y a donc aucune chaîne d'interface à traduire.

## 🔗 Projets liés

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Directement Liés**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé contre lequel chaque bridge valide déjà ses propres commandes ; la commande `gate` de ce hub (Livraison 3) appelle directement son propre `bridge_contract.evaluate_job()` réel pour une capacité write/abort, jamais une seconde implémentation de cette barrière.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — un nouveau projet frère : gère le cycle de vie des incidents de maintenance des propres composants de cet écosystème, tandis que ce hub découvre et valide ce qu'une machine/adaptateur EXTERNE peut faire.
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — explicitement PAS remplacé par ce projet : GATEWAY-INDUSTRIAL est un vrai relais de protocole avec sa propre liste blanche de commandes ; ce hub est un registre/validateur déclaratif qui se situe au-dessus de lui et de chaque autre bridge, jamais une seconde implémentation d'un protocole.

**Fait Également Partie de l'Écosystème**

*Matériel & Plateforme de Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la conception de la carte mère du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, destinée à coordonner jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA (firmware à un stade précoce ; aucune carte assemblée pour l'instant).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible sur Raspberry Pi OS pour le CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi de premier contact.

*Backend Central & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande d'essaim de bureau (PySide6) pour plusieurs serveurs à la fois.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et un compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran tactile DSI 7" embarqué, intégrée directement sur le CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui envoie les modèles terminés vers le propre catalogue de STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — éditeur de bureau de modèles STL, transformant/remplaçant/retirant/ajoutant de vraies pièces dans le même catalogue de modèles qu'édite aussi HYDRA-UMC-EDITOR-URDF.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour les flottes AGV/AMR via un éditeur MQTT VDA 5050 (testé uniquement contre une flotte émulée) ; le vrai `ownerProject` derrière la propre fixture `mobile-vda5050` de ce hub.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur haut niveau pour cellules CNC avec accès au statut/octets de contrôle GRBL (testé uniquement contre un émulateur) ; derrière la propre fixture `cnc-grbl` de ce hub.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un émetteur de commandes Boston Dynamics Spot (testé uniquement contre un émulateur).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de cellules laser lisant 3 signaux GPIO de clé/enceinte/verrouillage (testé uniquement contre une puce simulée ; il ne peut ni armer ni tirer un laser) ; derrière la propre fixture `laser-safety` de ce hub.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur haut niveau sûr pour le flux de cartes du pick-and-place OpenPnP ; derrière la propre fixture `pnp-openpnp` de ce hub.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec de vraies commandes de tâche contrôlées ; derrière la propre fixture `printer-moonraker` de ce hub.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur avec un transport ROS 2 rclpy à importation paresseuse (pas encore exécuté contre une installation ROS 2) ; derrière la propre fixture `robotics-ros2` de ce hub.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméra, avec un émetteur de commandes MAVLink (testé uniquement contre un émulateur) ; derrière la propre fixture `uav-mavlink` de ce hub.

*Plateforme d'Outils URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, plus de 25 profils d'outil sur bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau à interface graphique pour flasher les cartes URTC, CAN-OTA plus SWD/JTAG puce complète.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic CAN-bus en direct pour cartes URTC, un panneau par profil d'outil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée navigateur à URTC-TESTER via la Web Serial API, sans installation locale.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — passerelle devant le bus CAN d'URTC : liste d'identifiants autorisés, limite de débit et clé de session ; logiciel testé sur ordinateur, pas encore sur un bus réel.

*Nœud IA de Vision (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline de vision Hailo-8, avec une vraie vérification de disponibilité matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sécurisé par architecture Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + config MediaMTX, avec une vraie frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — loi de correction Position-Based Visual Servoing avec autorisation conditionnée à l'état de zone ; pas encore d'estimation de pose par caméra.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — logique v0 de violation de zone, de fraîcheur de calibration et de demande d'E-STOP qui lit les positions d'objets dans un fichier ; aucun détecteur ne l'alimente et aucun E-STOP physique n'y est encore relié.

*Nœud IA Cognitif (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub d'intégration pour le pipeline cognitif Hailo-10 (orchestration LLM/VLA/voix).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vrai encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vrai front-end vocal (VAD + analyseur d'intention) avec un relais Watch borné et soumis à confirmation.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vraie décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vraie recherche documentaire TF-IDF (bibliothèque standard uniquement) sur les propres documents Markdown de cet écosystème.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — technicien de maintenance IA local et à portes de politique pour l'écosystème lui-même - observe, diagnostique et propose des corrections ; les deux niveaux de risque les plus élevés ne sont délibérément pas encore implémentés.

*Orchestration & Essaim*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un vrai contrat de rapport de santé gRPC/Protobuf et une machine à états de mission.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vraie file de tâches basée sur la priorité avec déduplication, via une vraie API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vrai chien de garde de santé de flotte basé sur gRPC, avec retry/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vrai planificateur de trajectoire 3D basé sur RRT, avec vraie validation des collisions obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vraie synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un vrai contrat de synchronisation par compatibilité de version.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — routeur hardware-in-the-loop avec un verrouillage logiciel de collision entre simulation et matériel réel (testé sans matériel réel).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vraie cinématique directe et validation des limites articulaires sur un vrai sous-ensemble URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vrai générateur procédural de scènes 2D avec export d'annotations YOLO/COCO.

*Données & Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vrai magasin de séries temporelles basé sur sqlite3, avec une vraie API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vrai détecteur d'anomalies FFT + ligne de base statistique, avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vrai calcul OEE/disponibilité sur l'historique de DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vrai pipeline d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication par séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vrai espace d'adressage OPC-UA, vérifié avec une vraie session client du protocole binaire ; le vrai `ownerProject` derrière la propre fixture `industrial-opcua` de ce hub.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vrai broker MQTT avec authentification par client optionnelle et ACL de sujets ; derrière la propre fixture `industrial-mqtt` de ce hub.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — vrais points de terminaison XML MTConnect `/probe` et `/current`, avec sortie en mode dégradé ; derrière la propre fixture `manufacturing-mtconnect` de ce hub.

*Opérations de l'Écosystème*
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — détecte, installe et met à jour chaque checkout de l'écosystème.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — construit une image CM5 neuve et totalement à jour.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — hôte de développement reproductible (Raspberry Pi 5 / CM5) qui héberge le code source de l'écosystème et exécute des tâches de compilation/test délimitées via une file d'attente durable ; un rôle de développement dédié, explicitement distinct d'un CM5 opérationnel.
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux Smart Summaries et Anomaly Highlighting sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un vrai contrat de codes de sortie stable, un vrai client en direct de la propre API de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec des motifs d'alerte haptique et un relais vocal vers le téléphone jumelé (pas encore exécutée sur une montre physique).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un vrai compagnon de vision Python pour une tête d'outil d'inspection thermique/RGB.

## 📚 Documentation

Où lire la suite :

* [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md) - le contrat du manifeste d'adaptateur champ par champ
* [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) - comment une capacité passe la porte du SDK
* [docs/CERTIFICATION.md](docs/CERTIFICATION.md) - ce qu'est et n'est pas un enregistrement de certification
* [docs/MATURITY_CRITERIA.md](docs/MATURITY_CRITERIA.md) - quand un adaptateur compte comme plus mûr
* [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) - chaque commande et option, avec des sorties réelles capturées
* [Base de sécurité de l'écosystème](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Modèle de menaces de l'écosystème](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Journal des modifications de ce dépôt](CHANGELOG.md)
* [Licence de ce dépôt](LICENSE.md)

## 🤝 Contribuer et communauté

* Avant une pull request, exécutez `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (ou `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`) : il doit afficher `CI_VALIDATION=PASS`. N'exécutez pas `build.sh` ni `build.bat` pour cette vérification ; compiler n'est pas vérifier.
* Les huit README sont écrits à partir d'une source unique dans HYDRA-UMC-DOCS ; ne les modifiez pas à la main. Changez la source et réécrivez-les avec `tools/make_readmes.py`.
* N'affirmez pas dans un README ce qui n'a pas tourné : écrivez « simulé » ou « non essayé sur matériel » quand c'est la vérité.
* Voir [CONTRIBUTING.md](CONTRIBUTING.md), le [code de conduite](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) et [SUPPORT.md](SUPPORT.md).

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - [LICENSE](LICENSE).
