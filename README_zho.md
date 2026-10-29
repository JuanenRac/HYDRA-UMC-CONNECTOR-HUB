<!-- =============================================================================
HYDRA-UMC-CONNECTOR-HUB - Adapter-manifest registry
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🧩 面向外部机器适配器的声明式注册与校验工具

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

> **状态：v0.1.5，功能阶段——4 项交付中的全部 4 项(模式定义/CLI/fixture、只读目录、SDK 安全门、认证记录)均已交付。**
> `catalog`/`serve-catalog` 是真实的、仅支持 GET(整个项目中不存在任何网络写入路径)；`gate` 直接调用 HYDRA-UMC-SDK 自身真实的 `evaluate_job()`，绝不是该安全门的第二套实现(见 [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md))；`certify` 会记录一份真实的、由人类见证的证据，但明确**不会**独立地针对真实硬件去验证它——具体原因见 [docs/CERTIFICATION.md](docs/CERTIFICATION.md)，说明了为什么在没有实体机器在手的情况下这项工作必须保持在范围之外。关于当前真实存在的确切命令面，见 [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)。

> **诚实检查——今天真正可运行的部分：** 清单模式/校验器（`schema.py`）、只读目录（`registry.py`、`catalog_server.py`）、SDK 安全门集成（`sdk_gate.py`，它调用的是 `HYDRA-UMC-SDK` 自身真实的 `evaluate_job()`，针对的是一个真正安装好的检出版本，绝不是模拟）、认证日志（`certification.py`），以及 CLI（`cli.py`）都是真实的，并由 188 个通过的测试覆盖（`pytest tests/`，安装可选的 `[sdk]` 附加包时；没有它则跳过其中 34 个）。`certify` 会记录一份由人类见证的证据，但明确不会针对真实硬件对其进行独立验证——这 10 个 fixture 背后都没有实体机器，这里的任何适配器也从未被用来真正与一台真实设备通信过。`catalog`/`serve-catalog` 从设计上就只支持 GET（`catalog_server.py` 完全没有任何 `do_POST`/`do_PUT`）。详见上方的状态提示框，以及 `CHANGELOG.md` 中目前具体已交付的内容。

> **安全与安防现状:**本生态系统不是经认证的安全系统。目前尚无硬件 E-STOP 通路,没有由固件强制执行的限位或联锁,也没有经过验证的运动指令;固件映像使用 CRC32 和共享密钥的 HMAC-SHA256 校验,而非非对称签名;TLS 与双向 TLS 均为可选项,默认关闭;自制电路板尚未组装或测试。在依赖此处任何说法来保障人身安全之前,请先阅读[安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)和[威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.1.5` |
| 成熟度 | 可用 |
| 测试 | 188 (`python -m pytest -q tests`) |
| 技术栈 | Python 3.11+ / JSON Schema (hand-written structural validator, no jsonschema dependency) / http.server (stdlib-only real read-only catalog endpoint) / HYDRA-UMC-SDK (optional, real safety-gate integration via evaluate_job()) |
| 目标 | 使用者的电脑 |
| 真实硬件 | 尚未：此版本没有在真实硬件上运行的记录 |

**跳转：** [概述](#-概述) · [架构](#-架构) · [安全与防护](#-安全与防护) · [接口](#-接口) · [配置](#-配置) · [快速开始](#-快速开始) · [测试](#-测试) · [故障排除](#-故障排除) · [仓库结构](#-仓库结构) · [相关项目](#-相关项目)

## 🚦 项目状态

每一行是本仓库的一个部分，灯号表示它今天做到了哪一步。内容依据仓库能够展示的证据（测试、构建、运行），而不是计划。

🟢 已完成并验证 · 🟡 可用，有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不可用

| 领域 | 状态 | 在这里的含义 |
|---|---|---|
| 软件 | 🟡 | 主要用途可用；上面的诚实性检查列出了仍然缺少的内容 |
| 测试 | 🟢 | 188 项自动测试，每次变更都会运行 |
| 真实硬件 | 🔴 | 尚未：此版本没有在真实硬件上运行的记录 |
| 文档 | 🟢 | 八种语言的 README，每次变更都会与清单核对 |

## 🎯 概述

如今，某个单元/机器该使用哪一个桥接(bridge)，其选择与配置分散在众多真实 bridge 仓库自身的 README、`.env` 文件以及零散脚本之中。HYDRA-UMC-CONNECTOR-HUB 的定位，是成为唯一一个能对任意真实外部机器回答以下三个问题的地方：**它讲哪种协议、它到底能做什么(读取/写入/中止，各自伴随何种风险)，以及本生态系统中哪个已有的真实项目已经实现了它？**

本版本交付了该计划的全部四项，分为六个部分：

1. **一份真实且固定的契约**([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md))——本生态系统的"最小适配器契约(CONTRATO MINIMO DE ADAPTADOR)"，并且已经在代码中落实了一条不可协商的规则：一个 `write`/`abort` 能力，除非同时声明其风险等级、所需权限、所需单元状态、是否需要人工确认，以及超时时间，否则会被拒绝。
2. **一个真实的 CLI 校验器**(`hydra-umc-connector-hub validate`)——一段手写的结构性检查(不依赖 `jsonschema`)，因此每一条真实错误都会精确指出出问题的适配器/字段/能力。
3. **十个真实 fixture**，分别对应本生态系统中十个已经存在的真实 bridge/协议项目——证明该契约并非纸上谈兵，同时也是编写新适配器清单的起点模板。
4. **一个真实的只读目录**(`catalog`/`serve-catalog`)——发现某个目录中每一份结构有效的清单，并通过 `serve-catalog` 用一个真实的、仅支持 GET 的 `http.server` 暴露它们(整个项目中不存在任何写入路由)。
5. **与 HYDRA-UMC-SDK 安全门的真实集成**(`gate`)——一次 `write`/`abort` 能力调用会经由该 SDK 自身真实的 `evaluate_job()` 把关，绝不是该逻辑的第二套实现；见 [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)。
6. **真实的认证记录**(`certify`/`certifications`)——一份真实的、由人类见证的、仅追加的日志，会依据某个适配器自身的 `evidenceSchema` 进行校验；见 [docs/CERTIFICATION.md](docs/CERTIFICATION.md)，了解为什么独立针对真实硬件验证证据在此明确保持在范围之外。

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

整个项目中不存在任何默认/无参数调用方式，也没有图形界面——完整、真实的命令面见 [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)。

## 🧩 在 HYDRA-UMC 中的角色

**HYDRA-UMC-CONNECTOR-HUB** 描述外部机器如何接入生态系统，却不连接其中任何一台。适配器在清单中说明自己是什么、能做什么（读取、写入、中止）以及如何认证；中心负责校验、列出、让所请求的能力通过 SDK 的真实关口，并记录谁认证了什么。

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-CONNECTOR-HUB architecture" width="100%">
</p>

**为什么这样构建**

- **手写校验器，而非 `jsonschema`。** 交付 1 自身的契约足够小(14 个顶层字段，一种嵌套的能力结构)，以至于一个收集真实、具体错误字符串的简单 Python 函数，既比通用 JSON-Schema 校验器更简单，又能给出更清晰的输出——每条消息都会指出确切出问题的字段/下标，而不是一条泛泛的 schema 路径。
- **write/abort 安全规则由代码强制执行，而非只写在文档里。** `schema.py` 中的 `_WRITE_CAPABILITY_REQUIRED_FIELDS` 正是那条明确规则被转化成的真实、经过测试的检查——清单编写者不可能遗忘它，因为校验器会拒绝任何遗漏它的能力。
- **`authenticationRef` 被当作一个引用来检查，绝不被当作自由文本信任。** 一个封闭的真实前缀集合(`env:`、`secret-store:`、`vault:`、`none:`)——刻意不采用"看起来像秘密"式的启发式判断(为什么这种启发式在这个具体问题上同样是错误的工具，见 HYDRA-UMC-OPS-AGENT 自身的 `log_redaction.py`)。
- **每一条错误都会被收集，绝不只报告第一条。** `validate_adapter_manifest()` 在发现一个问题后会继续检查——修复清单的人能在一次运行中看到所有真实问题。
- **目录是刻意做成真实且只读的。** `registry.py` 对一个目录做非递归扫描(因此嵌套的 `fixtures/invalid/` 永远不会进入真实目录)，会丢弃——但依然报告——任何未通过 `validate_adapter_manifest()` 的内容，并拒绝两份声明同一个 `adapterId` 的文件。`catalog_server.py` 里任何地方都没有 `do_POST`/`do_PUT`——任何写入尝试都会得到 `BaseHTTPRequestHandler` 自身诚实的 `501`，绝不会有本项目忘记保护的路由。
- **安全门复用 HYDRA-UMC-SDK 自身真实的逻辑，绝非该逻辑的第二套实现。** `sdk_gate.py` 的 `evaluate_capability_call()` 会为每一个 `write`/`abort` 能力直接调用 `hydra_umc_sdk.bridge_contract.evaluate_job()`——`read` 能力则完全不会触碰该 SDK，因为 `evaluate_job()` 是一个运动/写入门，而非读取门。这项集成所做的唯一一处刻意且明确说明的简化(为任何非中止的写入操作使用单一的替代 `JobPhase`)，见 [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)。
- **认证记录对自己能证明什么、不能证明什么是诚实的。** `certification.py` 会拒绝保存一份证据与该适配器自身 `evidenceSchema` 不匹配的认证，但它从不宣称能够独立验证该证据确实来自真实硬件——本项目中任何地方都没有代码路径会打开一个真实的串口/OPC-UA 会话/MQTT 连接去做这项检查。见 [docs/CERTIFICATION.md](docs/CERTIFICATION.md)。
- **十个 fixture 都指向真实的所有者项目，绝非凭空捏造。** `fixtures/*.json` 中的每一个 `ownerProject` 都是本生态系统中一个真实存在的仓库(见相关项目章节)——这是一份真实的注册模板，而非空想出来的。
- **核心部分仅使用标准库。** `validate`/`catalog`/`serve-catalog`/`certify`/`certifications` 完全不需要任何依赖——`json`、纯 Python 结构性检查，以及 `http.server`。只有在一个 `write`/`abort` 能力上使用 `gate` 时才需要可选的 `[sdk]` extra。

## 🔒 安全与防护

| 威胁 | 防御 | 位置 |
|---|---|---|
| 冒充其他项目的适配器 | 所有者项目必须匹配 `^(HYDRA-UMC\|URTC)(-[A-Z0-9-]+)?$`，使用 `--ecosystem-root` 时还会对照该仓库的 `hydra-umc.project.json` 检查 | `schema.py`, `cli.py` |
| 清单中的凭据、巨大的清单、未知的模式 | `authenticationRef` 只接受前缀 `env:`、`secret-store:`、`vault:` 或 `none:`（绝不是机密本身）；清单最大 1 000 000 字节；能力模式为 `read`、`write`、`abort`，幂等性为 `none`、`idempotent`、`at-least-once` 或 `exactly-once` | `schema.py` |
| 绕过关口调用适配器、过期的请求 | `gate` 调用 SDK 自己的 `evaluate_job()`，绝不用第二套实现；要信任声明的状态须给 `--allow-unobserved`，并按清单要求给 `--human-confirmed`、`--safety-gate` 和 `--permission`；超过 30 秒的旧请求或超前超过 5 秒的请求会被拒绝 | `sdk_gate.py`, `cli.py` |
| 被篡改的认证记录和经网络的写入 | 记录构成由至少 16 个字符的密钥封存的哈希链（`.chain-head.json`、`.chain.lock`），`verify --strict` 遇到链外记录就会失败；`catalog` 和 `serve-catalog` 仅支持 GET：项目中不存在任何经网络的写入路径 | `ledger.py`, `catalog_server.py` |

**它绝不做的事：** 它从不接触机器，认证只保存人所证明的内容：证据不会对照真实硬件检查（见 `docs/CERTIFICATION.md`）。

## 🔌 接口

命令 `hydra-umc-connector-hub`（或 `./run.sh`）；完整参考见 `docs/CLI_REFERENCE.md`。目录也通过 HTTP 提供（仅 GET），默认在 `127.0.0.1:8801`。

| 主题或路由 | 内容 |
|---|---|
| `validate MANIFEST...` | 按契约校验清单 |
| `catalog --registry-dir DIR`, `serve-catalog --registry-dir DIR --port 8801` | 列出适配器，或以 GET 提供同一列表（`--ecosystem-root` 还会检查所有者项目） |
| `gate MANIFEST --capability ... --job-id ... --idempotency-key ... --source ... --cell-state ... --machine-state ...` | 让能力通过 SDK 关口（`--param k=v`、`--evidence-file`、`--allow-unobserved`、`--human-confirmed`、`--safety-gate`、`--permission`） |
| `certify`, `certifications`, `verify --strict` | 把某人的证明记入哈希链、列出记录、检查哈希链 |

## ⚙️ 配置

没有自己的环境变量：注册表文件夹、目录的主机和端口（`--registry-dir`、`--host`、`--port`）以及认证链的密钥（至少 16 个字符）都是命令行参数。适配器的凭据从不写在清单里，只写它们存放位置的引用。

## 🚀 快速开始

需要 Python 3.11 或更高版本；核心只用标准库（仅对写入或中止能力使用 `gate` 时才需要附加包 `sdk`，即 `pip install -e ".[sdk]"`）。

```bash
chmod +x build.sh   # 仅需一次
./build.sh          # 创建 .venv，pip install -e ".[dev]"，编译检查 + 测试
./run.sh                                   # 真实演示：校验十个真实 fixture
./run.sh validate fixtures/industrial-opcua.json
./run.sh validate fixtures/invalid/*.json  # 其中每一份都应报告 INVALID
./run.sh catalog --registry-dir fixtures
./run.sh serve-catalog --registry-dir fixtures --port 8801   # Ctrl+C 停止
pip install -e ".[sdk]"                    # 仅在对一个 write/abort 能力使用 `gate` 时需要
./run.sh gate fixtures/cnc-grbl.json --capability sendControlByte --job-id j1 \
    --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
./run.sh certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "你的名字" --evidence-file real-status.json --out-dir certifications/
```

在 Windows 上：先 `build.bat`，然后 `run.bat`（不带参数时执行同一演示）/
上面任意一个子命令。`build-test.sh`/`.bat` 执行与本项目自身 CI 相同的编译检查(仅 Python 语法)，不会改动项目版本或 CHANGELOG——但它自身并**不**运行测试套件；CI 会将 `pytest` 作为单独的、更晚的一个步骤来运行。要在本地运行完整的测试套件，请执行 `./build.sh`/`build.bat`(或直接执行 `pytest tests/`)。

**故障排查**

- `validate` 对一份你认为正确的清单报告 `INVALID`：请阅读列出的每一条原因——校验器会报告全部原因，而不只是第一条。字段级的确切契约见 [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)。
- `validate` 报告 `ERROR: ... is not valid JSON`：文件本身是格式错误的 JSON，这与"格式正确但内容无效"的清单是两回事——先检查是否漏了逗号或引号，再去检查契约本身。
- `catalog`/`serve-catalog` 以退出码 `1` 结束，或在 `invalidFiles` 中列出了某个文件：该文件未通过结构校验，因而被有意排除在目录之外——对它直接运行 `validate` 即可看到完整原因列表。
- `gate` 失败并报告 `ERROR: the optional 'hydra-umc-sdk' package is not installed`：先运行 `pip install -e ".[sdk]"`——只有 `write`/`abort` 能力才需要它。
- `gate`/`certify` 失败并报告 `ERROR: unknown cell_state ...` 或 `... does not match evidenceSchema`：确切的预期取值/形状见 [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)/[docs/CERTIFICATION.md](docs/CERTIFICATION.md)。

## 🧪 测试

运行 `python -m pytest -q tests` 会执行 188 个自动测试（其中 39 个需要附加包 `sdk`，没有它会被跳过）：模式与已发布的 JSON Schema、目录、SDK 关口、认证链、命令行和恶意输入。不需要硬件和外部网络。

CI 运行 `HYDRA_UMC_CI=1 python tools/ci_validate.py`，检查清单、文档、八个 README 和图片。

## 🏗️ 构建与发布

发布无需编译：`build.sh` / `build.bat` 创建虚拟环境、以可编辑模式安装包并运行测试，`build-test` 只做检查。构建从不改变版本；只有 `python tools/hydra_project_tool.py bump` 会提升版本，并同时推进更新日志。包、清单和更新日志的版本必须一致，否则 `ci_validate.py` 会失败。

## 🩺 故障排除

| 你看到 | 原因 | 处理 |
|---|---|---|
| `INVALID` on a manifest | 清单违反契约：所有者项目错误、`authenticationRef` 中有机密、未知模式或超过 1 000 000 字节 | 阅读 `validate` 的消息；`./run.sh validate fixtures/invalid/*.json` 展示每种失败 |
| `gate` refuses a write or abort capability | 未安装 SDK、状态未被观测，或缺少清单要求的确认 | `pip install -e ".[sdk]"`；给出 `--observed-machine-state`，或在接受声明状态时用 `--allow-unobserved`；按要求加上 `--human-confirmed`、`--safety-gate` 和 `--permission` |
| `verify --strict` fails | 有认证记录在哈希链之外，或密钥错误 | 使用封存该链的密钥（至少 16 个字符）；手工添加或编辑的记录按设计就在链之外 |

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-CONNECTOR-HUB" width="100%">
</p>

<details>
<summary>目录树的文本版本</summary>

```text
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py                                适配器清单的契约及其校验器
│   ├── registry.py                              把真实的桥接登记为适配器
│   ├── catalog_server.py                        仅 GET 的目录端点
│   ├── sdk_gate.py                              调用 SDK 自己的 evaluate_job()
│   ├── certification.py ledger.py               封存哈希链中的认证记录
│   └── cli.py                                   validate, catalog, serve-catalog, gate, certify
├── tests/                                       188 项测试
├── docs/                                        清单、关口、认证与成熟度指南
├── fixtures/                                    十个真实的适配器清单及无效示例
├── schemas/                                     已发布的 JSON Schema
├── tools/                                       构建与测试运行器、版本提升、CI 校验、README 与图片的生成和检查
├── images/                                      横幅图与 README 的图片
├── .github/                                     CI 工作流和 Issue 模板
├── pyproject.toml                               包元数据与依赖
├── hydra-umc.project.json                       清单：版本、成熟度、系列
├── CHANGELOG.md                                 每个版本的变化
├── build.sh build.bat                           构建脚本（从不改变版本）
├── build-test.sh build-test.bat                 构建脚本（从不改变版本）
├── test.sh test.bat                             运行测试
├── bump_version.py / bump_manifest_version.py   显式的版本提升
├── run.sh run.bat                               演示与命令
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE LICENSE.md
```

</details>

## 🗺️ 路线图与已知限制

**当前已知限制**

本项目自身清单和 CHANGELOG 中已经命名的 4 项交付计划，如今全部四项都已交付真实、经过测试的代码。诚实地说，尚剩：

- **交付 4 的硬件验证空白是刻意保留的。** `certify` 会记录一份由人类见证、依据某个适配器自身 `evidenceSchema` 校验过的证据，但本项目中没有任何东西能独立确认这份证据确实来自那台被指名的真实机器——这需要真正的实体硬件、在一个真实单元中，而这台开发机不具备。见 [docs/CERTIFICATION.md](docs/CERTIFICATION.md)。
- **真实客户端集成:已经开始,尚未完成。** HYDRA-UMC-SERVER 现在会真正轮询 `serve-catalog`——`GET /api/adapters` 与 `GET /api/adapters/:adapterId` 端到端地转发本项目自身的真实目录(见 HYDRA-UMC-SERVER 自身的 `tools/verify_connector_hub_relay_contract.mjs`,它会启动本项目真实的 `serve-catalog`、对接其真实的 `fixtures/` 以及一个真实的 Server 实例,绝非模拟)。该项目还被打包成真实的 wheel,安装到本项目自身检出目录之外的一个 venv 中并从那里运行,证明了打包本身(而不仅仅是可编辑安装)是可行的。让 Studio/Suite/Updater 自行调用 `gate` 仍是真实、独立、未来的工作。
- **`gate`/`certify` 调用方与真实单元/机器状态之间缺少真实传输通道。** 如今 `--cell-state`/`--machine-state` 都是由调用方作为已知值传入的——这里没有任何代码路径会从 HYDRA-UMC-SERVER 或某个安全区域服务实时获取它们。

## 🌍 语言

本 README 和仓库文档提供八种语言：英语、西班牙语、德语、法语、意大利语、日语、中文和葡萄牙语（葡萄牙）。它们同时编写，并由 CI 检查八个文件拥有相同的章节和相同的链接。 本仓库没有自己的界面或消息目录，因此没有需要翻译的界面文字。

## 🔗 相关项目

本项目是同一作者(JuanenRac / Electro Hobby 3D)打造的 HYDRA-UMC 机器人生态系统的一部分。值得了解,因为某个请求实际上可能是关于这些项目之一,而非本仓库本身。

**直接相关**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 每个桥接都已据此校验自身指令的共享 JSON-Schema 契约；本枢纽的 `gate` 命令(交付 3)会为一次 write/abort 能力调用直接调用其自身真实的 `bridge_contract.evaluate_job()`，绝不是该安全门的第二套实现。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 一个同类的新项目：负责运维本生态系统自身组件的维护事件生命周期，而本枢纽则负责发现并校验一台**外部**机器/适配器能做什么。
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 明确**不会**被本项目取代：GATEWAY-INDUSTRIAL 是一个拥有自身指令白名单的真实协议中继；本枢纽是一个位于它以及每一个其他 bridge 之上的声明式注册/校验层，绝非任何协议的第二套实现。

**生态系统中的其他项目**

*核心硬件与平台*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 机器人手臂主板设计——CM5 主机 + 双核 STM32H745,目标是通过 CAN-OTA/SPI-OTA 协调最多 8 条工具臂(固件处于早期阶段,尚无已组装的电路板)。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — 面向 CM5 的可复现 Raspberry Pi OS 产品层——只读代理、经过验证的配置/配置文件、WiFi 首次配网。

*核心后端与客户端*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — 每个控制客户端真正通信的真实无头后端(REST/WebSocket)。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — 具有实时多机器人 3D 可视化的网页控制面板。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 面向多台服务器的桌面(PySide6)集群指挥中心。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 具有生物识别登录和配对 Wear OS 伴侣应用的原生 Android 控制应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — 具有实时 WebSocket 同步的 iOS/iPadOS 控制应用(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 面向机载 7 英寸 DSI 触摸屏的原生触控界面，直接嵌入 CM5 本体。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 将完成的模型推送到 STUDIO 自身目录的桌面版图形化 URDF 创建/编辑工具。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — 桌面 STL 模型编辑器，在 HYDRA-UMC-EDITOR-URDF 编辑的同一模型目录中变换/替换/移除/添加真实部件。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 通过 VDA 5050 MQTT 发布者为 AGV/AMR 车队提供的协调边界(仅针对仿真车队测试)；本枢纽自身 `mobile-vda5050` fixture 背后真实的 `ownerProject`。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 具备 GRBL 状态/控制字节访问能力的高层 CNC 单元协调器(仅针对模拟器测试)；本枢纽自身 `cnc-grbl` fixture 背后的项目。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 面向足式/人形机器人的协调边界,带有 Boston Dynamics Spot 指令发送器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 读取 3 路钥匙/外壳/联锁 GPIO 信号的激光单元协调器(仅针对模拟芯片测试;无法使激光器上膛或发射)；本枢纽自身 `laser-safety` fixture 背后的项目。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — 面向 OpenPnP 贴片机板级流程的安全高层协调器；本枢纽自身 `pnp-openpnp` fixture 背后的项目。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 面向 Moonraker/Klipper 3D 打印机的安全协调边界，具备真实的受控作业指令；本枢纽自身 `printer-moonraker` fixture 背后的项目。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 带有惰性导入 rclpy ROS 2 传输层的协调器(尚未在 ROS 2 环境中运行)；本枢纽自身 `robotics-ros2` fixture 背后的项目。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 面向搭载摄像头的无人机的协调边界,带有 MAVLink 指令发送器(仅针对模拟器测试)；本枢纽自身 `uav-mavlink` fixture 背后的项目。

*URTC 工具平台*
- **[URTC](https://github.com/JuanenRac/URTC)** — 面向实体 Universal Robot Tool Controller 板卡的固件，通过 CAN 总线支持 25 种以上工具配置。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — 面向 URTC 板卡的桌面图形烧录工具，支持 CAN-OTA 以及全芯片 SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — 面向 URTC 板卡的桌面实时 CAN 总线诊断工具，每种工具配置对应一个面板。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — 通过 Web Serial API 实现的浏览器版 URTC-TESTER 替代方案，无需本地安装。
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — URTC CAN 总线前的网关：允许的标识符列表、速率限制和会话密钥；软件已在计算机上测试，尚未在真实总线上测试。

*视觉 AI 节点(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — 面向 Hailo-8 视觉流水线的集成中枢，具备逐阶段的真实硬件就绪检测。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — 具备 Hailo 架构/校验和安全加载验证的真实编译模型注册表。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 具备真实 HailoRT 集成边界的真实 GStreamer 流水线 + MediaMTX 配置生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 以区域状态为授权条件的 Position-Based Visual Servoing 修正律;尚无摄像头位姿估计。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 从文件读取物体位置的 v0 区域入侵、校准新鲜度与 E-STOP 请求逻辑;没有检测器为其供数,也尚未连接任何物理 E-STOP。

*认知 AI 节点(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — 面向 Hailo-10 认知流水线(LLM/VLA/语音编排)的集成中枢。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — 面向 Vision-Language-Action 模型的真实动作 token 编解码与轨迹生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 具备受限、需确认的 Watch 中继的真实语音前端(VAD + 意图解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — 基于真实规则的任务分解，以及针对 MCU 错误码的语义化错误恢复。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — 面向本生态系统自身 Markdown 文档的真实纯标准库 TF-IDF 文档检索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — 面向生态系统自身的本地、按策略门控的 AI 维护技师——观察、诊断并提出修复建议;两个最高风险等级目前特意尚未实现。

*编排与集群*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 具备真实 gRPC/Protobuf 健康报告契约与任务状态机的集成中枢。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 基于真实 HTTP API 的真实优先级任务队列，支持去重。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — 具备重试/退避与身份不匹配检测的真实基于 gRPC 的车队健康看门狗。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 具备真实障碍物/工作空间碰撞校验的真实基于 RRT 的三维路径规划器。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 经过多单元收敛属性测试的真实 CRDT LWW-Element-Map 状态同步。

*数字孪生与仿真*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 面向数字孪生引擎的集成中枢，具备真实的版本兼容性同步契约。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — 在仿真与真实硬件之间带有软件碰撞联锁的硬件在环路由器(未在真实硬件上测试)。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 面向真实 URDF 子集的真实正向运动学与关节限位校验。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — 具备 YOLO/COCO 标注导出功能的真实程序化 2D 场景生成器。

*数据与分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 具备真实数据摄入/查询 HTTP API 的真实 sqlite3 时序数据存储。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — 具备漂移监测能力的真实 FFT + 统计基线异常检测器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — 基于 DATALAKE 历史数据的真实 OEE/可用率计算，支持可复现的 CSV 导出。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — 面向 DATALAKE 的真实 CAN/WebSocket 数据摄入管道，支持序列去重。

*工业网关*
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 经真实二进制协议客户端会话验证的真实 OPC-UA 地址空间；本枢纽自身 `industrial-opcua` fixture 背后真实的 `ownerProject`。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — 具备可选按客户端认证与主题 ACL 的真实 MQTT 代理；本枢纽自身 `industrial-mqtt` fixture 背后的项目。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 具备降级模式输出的真实 MTConnect `/probe` 与 `/current` XML 端点；本枢纽自身 `manufacturing-mtconnect` fixture 背后的项目。

*生态系统运维*
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — 检测、安装并更新生态系统中的每一个检出目录。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — 构建一份全新、完全最新的 CM5 镜像。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 可复现的开发主机（Raspberry Pi 5 / CM5），保存整个生态系统的源代码，并在持久队列下运行有界的构建/测试任务；这是专用的开发角色，明确区别于运行中的 CM5。
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 基于 DATALAKE/ANOMALY-DETECTOR 的智能摘要与异常高亮面板，具备诚实的统计回退机制。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 具备真实、稳定退出码契约的车队 CLI，是 HYDRA-UMC-SERVER 自身 API 的真实在线客户端。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 带有触觉提醒模式与配对手机语音中继的 WearOS 伴侣应用(尚未在实体手表上运行)。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 面向板卡安装机架的固件，具备真实的工具 ID 解码与 Smart Idle 预热逻辑。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — 面向热成像/RGB 检测工具头的固件及真实 Python 视觉伴侣程序。

## 📚 文档

更多阅读：

* [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md) - 适配器清单契约（逐字段）
* [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) - 能力如何通过 SDK 关口
* [docs/CERTIFICATION.md](docs/CERTIFICATION.md) - 认证记录是什么、不是什么
* [docs/MATURITY_CRITERIA.md](docs/MATURITY_CRITERIA.md) - 适配器何时算更成熟
* [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) - 每个命令和选项，附真实捕获的输出
* [生态系统的安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [生态系统的威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [本仓库的更新日志](CHANGELOG.md)
* [本仓库的许可证](LICENSE.md)

## 🤝 参与贡献与社区

* 提交 pull request 之前，请运行 `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（或 `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）：它必须输出 `CI_VALIDATION=PASS`。此检查不要运行 `build.sh` 或 `build.bat`；构建不是检查。
* 八个 README 由 HYDRA-UMC-DOCS 中的同一个源生成；请勿手工编辑。修改源文件，再用 `tools/make_readmes.py` 重新生成。
* 不要在 README 中声称尚未运行过的内容：属实时请写“仅模拟”或“尚未在硬件上试过”。
* 请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)、[行为准则](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md) 和 [SUPPORT.md](SUPPORT.md)。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - [LICENSE](LICENSE).
