<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | 🇫🇷 <b>Français</b> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🧩 Un registre déclaratif et un validateur pour les adaptateurs de machines externes

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only core">
  <img src="https://img.shields.io/badge/Deliveries-4%20of%204-367BF5.svg" alt="4 livraisons sur 4">
</p>

> **État : v0.0.6, scaffolding - Livraisons 1-4 sur 4 (schéma/CLI/
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

---

## 1. 🛠️ VUE TECHNIQUE

Aujourd'hui, choisir et configurer quel bridge utilise une cellule/
machine donnée est réparti entre des README, des fichiers `.env` et des
scripts ad hoc dans de nombreux dépôts de bridges réels.
HYDRA-UMC-CONNECTOR-HUB est destiné à devenir l'unique endroit qui
répond, pour toute machine externe réelle, à trois questions : **quel
protocole parle-t-elle, que peut-elle vraiment faire (lire/écrire/
avorter, avec quel risque), et quel projet réel déjà existant de cet
écosystème l'implémente déjà ?**

Cette version expédie les quatre livraisons prévues :

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

$ hydra-umc-connector-hub gate fixtures/cnc-grbl.json --capability sendControlByte \
    --job-id j1 --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
{"allowed": true, "reason": "cell and external machine are ready", "evidenceErrors": []}

$ hydra-umc-connector-hub certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Juan Enrique" --evidence-file real-status.json --out-dir certifications/
CERTIFIED adapterId='cnc-grbl' certificationId='...' -> certifications/cnc-grbl__....json
```

Il n'existe ni invocation par défaut/sans argument ni GUI nulle part
dans ce projet - voir [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)
pour la surface de commandes complète et réelle.

## 2. 🧱 ARCHITECTURE ET DÉCISIONS DE CONCEPTION

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

## 📂 STRUCTURE DES RÉPERTOIRES

```
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py            # Le vrai contrat adapter-manifest + validateur structurel + vérificateur de sous-ensemble JSON-Schema
│   ├── registry.py          # Livraison 2 : scanne un répertoire vers un vrai catalogue stable et trié
│   ├── catalog_server.py    # Livraison 2 : vrai http.server uniquement GET exposant le catalogue
│   ├── sdk_gate.py          # Livraison 3 : vraie intégration evaluate_job() de HYDRA-UMC-SDK
│   ├── certification.py     # Livraison 4 : vrai journal de certification en ajout seul, attesté par un humain
│   └── cli.py               # Point d'entrée validate/catalog/serve-catalog/gate/certify/certifications
├── fixtures/                # Dix vrais manifestes d'adaptateur valides (un par bridge existant)
│   └── invalid/             # Cinq vrais manifestes invalides, chacun démontrant une raison de rejet
├── tests/                   # Vrais tests : fixtures, un vrai http.server sur un port éphémère, le vrai hydra-umc-sdk installé, et un vrai journal de certification dans un répertoire temporaire
├── docs/
│   ├── ADAPTER_MANIFEST.md  # Le contrat réel complet, champ par champ
│   ├── CAPABILITY_GATE.md   # Le propre contrat réel de la barrière de la Livraison 3 et son unique simplification nommée
│   ├── CERTIFICATION.md     # Le propre contrat réel de la Livraison 4 et son manque honnête de vérification matérielle
│   └── CLI_REFERENCE.md     # Chaque sous-commande, ses formes de sortie, le contrat des codes de sortie
├── images/                  # Médias et icônes de l'application
├── tools/
│   ├── build_test.py        # Vérification de build/compilation sans versionnage
│   └── ci_validate.py       # Validation manifeste/CHANGELOG/docs utilisée par la CI
├── build.sh / build.bat     # venv + installation éditable + compile-check + tests
├── build-test.sh / .bat     # Validation de build uniquement, sans rien modifier
├── run.sh / run.bat         # Démo réelle : valide les dix fixtures (sans argument), ou relaie une vraie commande CLI
├── bump_version.py          # Incrément type "odomètre" de l'écosystème (pyproject.toml + __init__.py)
└── bump_manifest_version.py # Synchronise la version de hydra-umc.project.json avec la native (--sync)
```

## ⚙️ COMPILATION ET EXÉCUTION

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

## 🚀 FEUILLE DE ROUTE

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

## 🔗 Projets Liés

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Directement Liés**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé contre lequel chaque bridge valide déjà ses propres commandes ; la commande `gate` de ce hub (Livraison 3) appelle directement son propre `bridge_contract.evaluate_job()` réel pour une capacité write/abort, jamais une seconde implémentation de cette barrière.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — un nouveau projet frère : gère le cycle de vie des incidents de maintenance des propres composants de cet écosystème, tandis que ce hub découvre et valide ce qu'une machine/adaptateur EXTERNE peut faire.
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — explicitement PAS remplacé par ce projet : GATEWAY-INDUSTRIAL est un vrai relais de protocole avec sa propre liste blanche de commandes ; ce hub est un registre/validateur déclaratif qui se situe au-dessus de lui et de chaque autre bridge, jamais une seconde implémentation d'un protocole.

**Fait Également Partie de l'Écosystème**

*Matériel & Plateforme de Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère physique du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, coordonnant jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible sur Raspberry Pi OS pour le CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi de premier contact.

*Backend Central & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande d'essaim de bureau (PySide6) pour plusieurs serveurs à la fois.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et un compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran tactile DSI 7" embarqué, intégrée directement sur le CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui envoie les modèles terminés vers le propre catalogue de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour les flottes AGV/AMR via un éditeur MQTT VDA 5050 réel ; le vrai `ownerProject` derrière la propre fixture `mobile-vda5050` de ce hub.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur haut niveau pour cellules CNC avec accès réel au statut/octets de contrôle GRBL ; derrière la propre fixture `cnc-grbl` de ce hub.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un véritable émetteur de commandes Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de sécurité pour cellules laser lisant 3 vraies sécurités GPIO de clé/enceinte/verrouillage ; derrière la propre fixture `laser-safety` de ce hub.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur haut niveau sûr pour le flux de cartes du pick-and-place OpenPnP ; derrière la propre fixture `pnp-openpnp` de ce hub.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec de vraies commandes de tâche contrôlées ; derrière la propre fixture `printer-moonraker` de ce hub.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur de sécurité avec un vrai transport ROS 2 rclpy à importation paresseuse ; derrière la propre fixture `robotics-ros2` de ce hub.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméra, avec un véritable émetteur de commandes MAVLink ; derrière la propre fixture `uav-mavlink` de ce hub.

*Plateforme d'Outils URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, plus de 25 profils d'outil sur bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau à interface graphique pour flasher les cartes URTC, CAN-OTA plus SWD/JTAG puce complète.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic CAN-bus en direct pour cartes URTC, un panneau par profil d'outil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée navigateur à URTC-TESTER via la Web Serial API, sans installation locale.

*Nœud IA de Vision (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline de vision Hailo-8, avec une vraie vérification de disponibilité matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sécurisé par architecture Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + config MediaMTX, avec une vraie frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vraie loi de correction Position-Based Visual Servoing, verrouillée sur l'état de zone en amont.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vraie vérification de violation de zone et demande d'E-STOP, avec application de la fraîcheur de calibration.

*Nœud IA Cognitif (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub d'intégration pour le pipeline cognitif Hailo-10 (orchestration LLM/VLA/voix).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vrai encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vrai front-end vocal (VAD + analyseur d'intention) avec un relais Watch borné et soumis à confirmation.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vraie décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vraie recherche documentaire TF-IDF (bibliothèque standard uniquement) sur les propres documents Markdown de cet écosystème.

*Orchestration & Essaim*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un vrai contrat de rapport de santé gRPC/Protobuf et une machine à états de mission.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vraie file de tâches basée sur la priorité avec déduplication, via une vraie API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vrai chien de garde de santé de flotte basé sur gRPC, avec retry/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vrai planificateur de trajectoire 3D basé sur RRT, avec vraie validation des collisions obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vraie synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un vrai contrat de synchronisation par compatibilité de version.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vrai verrouillage de sécurité hardware-in-the-loop routant les commandes entre simulation et matériel réel.
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec de vraies alertes haptiques et un relais vocal vers le téléphone jumelé.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un vrai compagnon de vision Python pour une tête d'outil d'inspection thermique/RGB.

---

## 📚 Documentation & Communauté

- **[docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)** — le contrat réel complet, champ par champ, et pourquoi `authenticationRef` est une référence.
- **[docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)** — la propre intégration réelle de la Livraison 3 avec la barrière de sécurité de HYDRA-UMC-SDK et son unique simplification nommée.
- **[docs/CERTIFICATION.md](docs/CERTIFICATION.md)** — le propre contrat réel de journal de certification de la Livraison 4 et son manque honnête de vérification matérielle.
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — chaque sous-commande, ses formes de sortie, et le contrat des codes de sortie.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pile technologique et lignes directrices de codage pour une pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — les normes de comportement attendues dans cette communauté.
- **[SECURITY.md](SECURITY.md)** — comment signaler une vulnérabilité, et les véritables axes de sécurité de ce projet.
- **[SUPPORT.md](SUPPORT.md)** — où poser des questions et signaler des bugs.

## 👤 AUTEUR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCE

GPL-3.0 (logiciel) / CC BY-SA 4.0 (documentation) - voir [LICENSE.md](LICENSE.md).
