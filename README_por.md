<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | 🇵🇹 <b>Português</b></p>

### 🧩 Um registo declarativo e validador de adaptadores de máquinas externas

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only core">
  <img src="https://img.shields.io/badge/Deliveries-4%20of%204-367BF5.svg" alt="Deliveries 4 of 4">
</p>

> **Estado: v0.1.3, funcional - Entregas 1-4 de 4 (esquema/CLI/
> dados de teste, catálogo só de leitura, porta de segurança do SDK, registos de certificação).**
> `catalog`/`serve-catalog` são reais e só de GET (não existe nenhum caminho de
> escrita pela rede em todo este projeto); `gate` chama diretamente o
> `evaluate_job()` real do próprio HYDRA-UMC-SDK, nunca uma segunda
> implementação dessa porta (veja
> [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)); `certify` regista
> uma prova real atestada por uma pessoa, mas explicitamente NÃO a verifica
> de forma independente contra hardware real - veja
> [docs/CERTIFICATION.md](docs/CERTIFICATION.md) para saber exatamente porque é que isso
> fica fora do âmbito sem uma máquina física à mão. Veja
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) para a superfície exata de
> comandos que existe hoje.

> **Verificação de honestidade - o que realmente funciona hoje:** o esquema/validador de manifestos (`schema.py`), o catálogo só de leitura (`registry.py`, `catalog_server.py`), a integração da porta de segurança do SDK (`sdk_gate.py`, que chama o `evaluate_job()` real do próprio `HYDRA-UMC-SDK` contra uma cópia real instalada, nunca um simulado), o registo de certificação (`certification.py`) e a CLI (`cli.py`) são reais e estão cobertos por 165 testes a passar (`pytest tests/`, com o extra opcional `[sdk]` instalado - 34 deles são ignorados sem ele). O `certify` regista uma prova atestada por uma pessoa, mas explicitamente não a verifica de forma independente contra hardware real - não há nenhuma máquina física por trás de qualquer um dos 10 dados de teste, e nenhum adaptador aqui foi alguma vez usado para falar de facto com um dispositivo real. `catalog`/`serve-catalog` são só de GET por construção (o `catalog_server.py` não tem sequer `do_POST`/`do_PUT`). Veja a caixa de Estado acima e o `CHANGELOG.md` para saber exatamente o que foi entregue até agora.

---

## 1. 🛠️ VISÃO TÉCNICA GERAL

Hoje, escolher e configurar que bridge uma dada célula/máquina usa está
espalhado por READMEs, ficheiros `.env` e scripts avulsos em muitos
repositórios reais de bridges. O HYDRA-UMC-CONNECTOR-HUB destina-se a tornar-se o
único sítio que responde, para qualquer máquina externa real, a três
perguntas: **que protocolo fala, o que consegue realmente fazer
(ler/escrever/abortar, com que risco) e que projeto real já existente deste
ecossistema o implementa?**

Esta versão entrega as quatro entregas planeadas:

1. **Um contrato real e fixo** ([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)) -
   o "CONTRATO MINIMO
   DE ADAPTADOR" deste ecossistema, com uma regra inegociável imposta em código: uma
   capacidade `write`/`abort` é rejeitada a menos que declare também o seu
   próprio risco, a permissão exigida, o estado da célula exigido, a exigência
   de confirmação humana e o tempo limite.
2. **Um validador de CLI real** (`hydra-umc-connector-hub validate`) - uma
   verificação estrutural escrita à mão (sem dependência do `jsonschema`), para que cada
   erro real nomeie o adaptador/campo/capacidade exato em falta.
3. **Dez dados de teste reais**, um por cada projeto de bridge/protocolo real já
   existente neste ecossistema - prova de que o contrato não é
   teórico e um modelo de partida para um novo manifesto de adaptador.
4. **Um catálogo real só de leitura** (`catalog`/`serve-catalog`) -
   descobre todos os manifestos estruturalmente válidos de uma pasta e, no
   `serve-catalog`, expõe-os através de um `http.server` real só de GET (não existe
   nenhuma rota de escrita em todo este projeto).
5. **Uma integração real da porta de segurança do HYDRA-UMC-SDK** (`gate`) - uma
   chamada a uma capacidade `write`/`abort` é controlada pelo `evaluate_job()` real
   do próprio SDK, nunca por uma segunda implementação dessa lógica; veja
   [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md).
6. **Registos de certificação reais** (`certify`/`certifications`) - um
   registo só de acrescento, atestado por uma pessoa, verificado contra o próprio
   `evidenceSchema` do adaptador; veja [docs/CERTIFICATION.md](docs/CERTIFICATION.md)
   para saber porque é que verificar de forma independente a prova contra hardware real fica
   explicitamente fora do âmbito aqui.

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

Não existe invocação por omissão nem sem argumentos, nem interface gráfica em todo este projeto
- veja [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) para a superfície real e
completa de comandos.

## 2. 🧱 ARQUITETURA E DECISÕES DE DESENHO

- **Um validador escrito à mão, não o `jsonschema`.** O contrato da Entrega 1 é
  pequeno o suficiente (14 campos de topo, uma forma aninhada de capacidade) para que uma
  função Python simples que recolhe cadeias de erro reais e específicas seja ao mesmo tempo
  mais simples do que um validador genérico de JSON-Schema E
  produza uma saída mais clara - cada mensagem nomeia o campo/índice exato em
  falta, não um caminho de esquema genérico.
- **A regra de segurança de escrita/aborto é imposta em código, não na documentação.**
  `_WRITE_CAPABILITY_REQUIRED_FIELDS` em `schema.py` é essa regra explícita
  convertida numa verificação real e testada - o autor de um
  manifesto não se pode esquecer dela, porque o validador rejeita uma
  capacidade que a esqueça.
- **O `authenticationRef` é verificado como referência, nunca aceite como
  texto livre.** Um conjunto fechado de prefixos reais (`env:`, `secret-store:`,
  `vault:`, `none:`) - deliberadamente não uma heurística de "parece um
  segredo" (veja o `log_redaction.py` do próprio HYDRA-UMC-OPS-AGENT para saber porque é que uma
  heurística é a ferramenta errada também para este mesmo problema).
- **Todos os erros são recolhidos, nunca apenas o primeiro.**
  O `validate_adapter_manifest()` continua a verificar depois de encontrar um problema -
  quem corrige um manifesto vê todos os problemas reais numa só execução.
- **O catálogo é real e só de leitura, de propósito.** O `registry.py` percorre
  uma pasta sem recursão (para que uma `fixtures/invalid/` aninhada nunca
  entre num catálogo real), descarta - mas continua a reportar - tudo o que falhe
  no `validate_adapter_manifest()`, e rejeita dois ficheiros que declarem o
  mesmo `adapterId`. O `catalog_server.py` não tem `do_POST`/`do_PUT`
  em lado nenhum - uma tentativa de escrita recebe o `501` honesto do próprio
  `BaseHTTPRequestHandler`, nunca uma rota que este projeto se esqueceu de proteger.
- **A porta de segurança reutiliza a lógica real do HYDRA-UMC-SDK, nunca uma
  segunda implementação dela.** O `evaluate_capability_call()` do `sdk_gate.py`
  chama diretamente o `hydra_umc_sdk.bridge_contract.evaluate_job()` para
  cada capacidade `write`/`abort` - uma capacidade `read` nunca toca no SDK,
  já que o `evaluate_job()` é uma porta de movimento/escrita, não de leitura. Veja
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) para a única simplificação
  deliberada e assumida desta integração
  (uma só `JobPhase` de substituição para qualquer escrita que não seja um aborto).
- **Um registo de certificação é honesto sobre o que pode e não pode
  provar.** O `certification.py` recusa guardar uma certificação cuja
  prova não corresponda ao `evidenceSchema` do próprio adaptador, mas
  nunca afirma verificar de forma independente que a prova veio de hardware
  real - não existe nenhum caminho de código neste projeto que abra uma
  porta série/sessão OPC-UA/ligação MQTT reais para o verificar. Veja
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Os dez dados de teste nomeiam projetos proprietários reais, nunca inventados.**
  Cada `ownerProject` em `fixtures/*.json` é um repositório verdadeiro deste
  ecossistema (veja a secção Projetos relacionados) - isto é um modelo real
  de registo, não um especulativo.
- **Só a biblioteca padrão para o núcleo.** `validate`/`catalog`/`serve-catalog`/
  `certify`/`certifications` não precisam de nenhuma dependência - `json`, verificações
  estruturais simples em Python e `http.server`. Só o `gate` numa capacidade
  `write`/`abort` precisa do extra opcional `[sdk]`.

## 📂 ESTRUTURA DE DIRETÓRIOS

```
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py            # O contrato real do manifesto de adaptador + validador estrutural + verificador de subconjunto de JSON-Schema
│   ├── registry.py          # Entrega 2: percorre uma pasta e produz um catálogo real, estável e ordenado
│   ├── catalog_server.py    # Entrega 2: http.server real só de GET que expõe o catálogo
│   ├── sdk_gate.py          # Entrega 3: integração real com o evaluate_job() do HYDRA-UMC-SDK
│   ├── certification.py     # Entrega 4: registo de certificação real, só de acrescento, atestado por uma pessoa
│   └── cli.py               # Ponto de entrada validate/catalog/serve-catalog/gate/certify/certifications
├── fixtures/                # Dez manifestos de adaptador reais e válidos (um por cada bridge existente)
│   └── invalid/             # Cinco manifestos inválidos reais, cada um a demonstrar um motivo de rejeição
├── tests/                   # Testes reais: dados de teste, um http.server real numa porta efémera, o hydra-umc-sdk real instalado e um registo de certificação real numa pasta temporária
├── docs/
│   ├── ADAPTER_MANIFEST.md  # O contrato real completo, campo a campo
│   ├── CAPABILITY_GATE.md   # O contrato real da porta da Entrega 3 e a sua única simplificação assumida
│   ├── CERTIFICATION.md     # O contrato real da Entrega 4 e a sua lacuna honesta de verificação em hardware
│   └── CLI_REFERENCE.md     # Cada subcomando, as suas formas de saída, códigos de saída
├── images/                  # Multimédia e ícones da aplicação
├── tools/
│   ├── build_test.py        # Verificação de compilação sem subida de versão
│   └── ci_validate.py       # Validação de manifesto/CHANGELOG/documentação usada pelo CI
├── build.sh / build.bat     # venv + instalação editável + verificação de compilação + testes
├── build-test.sh / .bat     # Apenas validação de compilação sem alterações
├── run.sh / run.bat         # Demonstração real: valida os dez dados de teste (sem argumentos) ou reencaminha um comando real da CLI
├── bump_version.py          # Subida "conta-quilómetros" do ecossistema (pyproject.toml + __init__.py)
└── bump_manifest_version.py # Sincroniza a versão do hydra-umc.project.json com a nativa (--sync)
```

## ⚙️ GUIA DE COMPILAÇÃO E EXECUÇÃO

```bash
chmod +x build.sh   # uma só vez
./build.sh          # cria o .venv, pip install -e ".[dev]", verificação de compilação + testes
./run.sh                                   # demonstração real: valida os dez dados de teste reais
./run.sh validate fixtures/industrial-opcua.json
./run.sh validate fixtures/invalid/*.json  # cada um destes deve reportar INVALID
./run.sh catalog --registry-dir fixtures
./run.sh serve-catalog --registry-dir fixtures --port 8801   # Ctrl+C para parar
pip install -e ".[sdk]"                    # só necessário para o `gate` numa capacidade write/abort
./run.sh gate fixtures/cnc-grbl.json --capability sendControlByte --job-id j1 \
    --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
./run.sh certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Your Name" --evidence-file real-status.json --out-dir certifications/
```

No Windows: `build.bat` e depois `run.bat` (a mesma demonstração quando chamado sem
argumentos) / qualquer um dos subcomandos acima. O `build-test.sh`/`.bat`
faz a mesma verificação não alteradora de sintaxe Python que o fluxo de CI
deste projeto faz, sem tocar na versão do projeto nem no CHANGELOG - NÃO executa a suite de testes
em si; o CI executa o `pytest` como um passo separado e posterior. Execute `./build.sh`/`build.bat`
(ou o `pytest tests/` diretamente) para a suite de testes local completa.

**Resolução de problemas**

- `validate` reporta `INVALID` para um manifesto que acredita estar correto:
  leia todos os motivos listados - o validador reporta todos, não apenas
  o primeiro. Veja [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)
  para o contrato exato, campo a campo.
- `validate` reporta `ERROR: ... is not valid JSON`: o próprio ficheiro está
  malformado como JSON, o que é distinto de um manifesto bem formado mas inválido -
  procure uma vírgula/aspas em falta antes de verificar o contrato propriamente dito.
- `catalog`/`serve-catalog` termina com `1` ou lista um ficheiro em
  `invalidFiles`: esse ficheiro falhou a validação estrutural e foi deixado
  fora do catálogo de propósito - execute o `validate` sobre ele diretamente para obter a
  lista completa de motivos.
- `gate` falha com `ERROR: the optional 'hydra-umc-sdk' package is not
  installed`: execute primeiro `pip install -e ".[sdk]"` - só necessário para uma
  capacidade `write`/`abort`.
- `gate`/`certify` falha com `ERROR: unknown cell_state ...` ou
  `... does not match evidenceSchema`: veja
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)/
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md) para os valores/formas
  reais exatos esperados.

## 🚀 ROTEIRO

As quatro entregas do plano indicado no próprio manifesto e CHANGELOG deste projeto
entregam agora código real e testado. O que falta, dito com honestidade:

- **A lacuna de verificação em hardware da Entrega 4 fica aberta de propósito.**
  O `certify` regista uma prova atestada por uma pessoa, verificada contra o
  `evidenceSchema` do próprio adaptador, mas nada neste projeto
  confirma de forma independente que a prova veio da máquina real indicada
  - isso exige o próprio hardware físico, numa célula real,
  que esta máquina de desenvolvimento não tem. Veja
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Integração real com clientes: iniciada, não concluída.** O HYDRA-UMC-SERVER já
  consulta o `serve-catalog` a sério - `GET /api/adapters` e
  `GET /api/adapters/:adapterId` reencaminham o catálogo real deste projeto, de ponta
  a ponta (veja o `tools/verify_connector_hub_relay_contract.mjs` do próprio HYDRA-UMC-SERVER,
  que arranca o `serve-catalog` real deste projeto contra os seus `fixtures/` reais e uma instância
  real do Servidor, nunca um simulado). Isto foi também instalado como uma wheel real num venv fora da
  cópia deste projeto e executado a partir daí, confirmando que o próprio empacotamento (não
  apenas uma instalação editável) funciona. O Studio/Suite/Updater chamarem o `gate`
  eles próprios continua a ser trabalho real, separado e futuro.
- **Um transporte real entre quem chama o `gate`/`certify` e o estado real
  da célula/máquina.** Hoje, `--cell-state`/`--machine-state` são
  fornecidos por quem chama como valores já conhecidos - não existe nenhum caminho de código
  aqui que os obtenha em direto do HYDRA-UMC-SERVER ou de um serviço de zonas de segurança.

---

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, porque um pedido pode ser, na verdade, sobre um destes e não sobre este repositório.

**Diretamente relacionados**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado contra o qual cada bridge já valida os seus próprios comandos; o comando `gate` deste hub (Entrega 3) chama diretamente o seu `bridge_contract.evaluate_job()` real para uma capacidade de escrita/aborto, nunca uma segunda implementação dessa porta.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — um projeto novo e irmão: opera o ciclo de vida dos incidentes de manutenção dos componentes PRÓPRIOS deste ecossistema, enquanto este hub descobre e valida o que uma máquina/adaptador EXTERNO consegue fazer.
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — explicitamente NÃO substituído por este projeto: o GATEWAY-INDUSTRIAL é um relé de protocolos real com a sua própria lista de comandos permitidos; este hub é um registo/validador declarativo que fica acima dele e de todas as outras bridges, nunca uma segunda implementação de qualquer protocolo.

**Também fazem parte do ecossistema**

*Hardware e plataforma centrais*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — a placa-mãe física do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, que orquestra até 8 braços de ferramenta por CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reproduzível do Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, aprovisionamento Wi-Fi de primeiro contacto.

*Backend central e clientes*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o back-end headless real (REST/WebSocket) com que todos os clientes de controlo realmente comunicam.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel web de controlo com visualização 3D em tempo real de vários robôs.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de comando de enxame para desktop (PySide6) para vários servidores ao mesmo tempo.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação Android nativa de controlo, com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, executada no próprio CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o catálogo do STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop que transforma/substitui/remove/adiciona peças reais no mesmo catálogo de modelos que o HYDRA-UMC-EDITOR-URDF também edita.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 real; o `ownerProject` real por detrás do dado de teste `mobile-vda5050` deste hub.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso real ao estado GRBL e aos bytes de controlo; por detrás do dado de teste `cnc-grbl` deste hub.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor real de comandos para o Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de segurança de células laser que lê 3 proteções reais por GPIO (chave, caixa e interlock); por detrás do dado de teste `laser-safety` deste hub.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de fluxo de placa de alto nível para pick-and-place com OpenPnP; por detrás do dado de teste `pnp-openpnp` deste hub.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por portas; por detrás do dado de teste `printer-moonraker` deste hub.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador de segurança com um transporte ROS 2 real baseado em rclpy importado sob demanda; por detrás do dado de teste `robotics-ros2` deste hub.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor real de comandos MAVLink; por detrás do dado de teste `uav-mavlink` deste hub.

*Plataforma de ferramentas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware da placa física Universal Robot Tool Controller, mais de 25 perfis de ferramenta por barramento CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — ferramenta gráfica de gravação para desktop das placas URTC, por CAN-OTA e também SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — ferramenta de diagnóstico CAN em tempo real para desktop das placas URTC, com um painel por perfil de ferramenta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa no navegador ao URTC-TESTER através da Web Serial API, sem instalação local.

*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integração do pipeline de visão Hailo-8, com uma verificação real de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carga por arquitetura Hailo e soma de verificação.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real e gerador de configuração MediaMTX com uma fronteira de integração HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção real de servovisão baseada em posição, protegida pelo estado da zona a montante.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — verificação real de violação de zonas e pedido de E-STOP, com exigência de calibração recente.

*Nó de IA cognitiva (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integração do pipeline cognitivo do Hailo-10 (orquestração de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Visão-Linguagem-Ação.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analisador de intenções) com um relé para o relógio limitado e protegido por confirmação.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre os códigos de erro do MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF só com a biblioteca padrão sobre a documentação Markdown deste ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local, protegido por políticas, para o próprio ecossistema: observa, diagnostica e propõe correções; os dois níveis de maior risco não estão implementados de propósito.

*Orquestração e enxame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integração com um contrato real de relatório de saúde gRPC/Protobuf e uma máquina de estados de missões.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila real de trabalhos por prioridade com deduplicação, sobre uma API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de saúde da frota por gRPC com repetição/recuo e deteção de identidade incoerente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador real de trajetórias 3D baseado em RRT com validação real de colisões com obstáculos e espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para a convergência de várias células.

*Gémeo digital e simulação*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — centro de integração do motor de gémeo digital, com um contrato real de sincronização de compatibilidade de versões.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — interlock de segurança real de hardware-in-the-loop que encaminha comandos entre a simulação e o hardware real.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática direta real e validação de limites de juntas sobre um subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gerador procedural real de cenas 2D com exportação de anotações YOLO/COCO.

*Dados e análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazém real de séries temporais sobre sqlite3 com uma API HTTP real de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias por FFT e linha de base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reprodutível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway industrial*
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma sessão real de cliente em protocolo binário; o `ownerProject` real por detrás do dado de teste `industrial-opcua` deste hub.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACLs de tópicos; por detrás do dado de teste `industrial-mqtt` deste hub.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reais `/probe` e `/current` do MTConnect, com saída em modo degradado; por detrás do dado de teste `manufacturing-mtconnect` deste hub.

*Operações do ecossistema*
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — deteta, instala e atualiza cada cópia de trabalho do ecossistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — constrói uma imagem do CM5 nova e totalmente atualizada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que guarda o código-fonte do ecossistema e executa tarefas limitadas de compilação/teste numa fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis de Resumos Inteligentes e Realce de Anomalias sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI da frota com um contrato de códigos de saída real e estável, um cliente vivo genuíno da API do HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com alertas hápticos reais e um relé de voz para o telemóvel emparelhado.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware de um rack de montagem de placas com descodificação real do ID da ferramenta e lógica de pré-aquecimento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um companheiro de visão em Python real para uma cabeça de ferramenta de inspeção térmica/RGB.

---

## 📚 Documentação e comunidade

- **[docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)** — o contrato real completo, campo a campo, e porque é que o `authenticationRef` é uma referência.
- **[docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)** — a integração real da porta de segurança do HYDRA-UMC-SDK da Entrega 3 e a sua única simplificação assumida.
- **[docs/CERTIFICATION.md](docs/CERTIFICATION.md)** — o contrato real de registo de certificação da Entrega 4 e a sua lacuna honesta de verificação em hardware.
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — cada subcomando, as suas formas de saída e o contrato de códigos de saída.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pilha tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como comunicar uma vulnerabilidade e as áreas de segurança em que este projeto se concentra.
- **[SUPPORT.md](SUPPORT.md)** — onde fazer perguntas e comunicar erros.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENÇA

GPL-3.0 (software) / CC BY-SA 4.0 (documentação) - veja [LICENSE.md](LICENSE.md).

