<!-- =============================================================================
HYDRA-UMC-CONNECTOR-HUB - Adapter-manifest registry
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🧩 外部マシン用アダプターのための宣言的レジストリとバリデーター

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

> **ステータス: v0.1.6、functional(機能段階) - 4 件の納品のうち全 4 件(スキー
> マ/CLI/フィクスチャ、読み取り専用カタログ、SDK 安全ゲート、認証記
> 録)完了。** `catalog`/`serve-catalog` は本物で GET のみです(このプ
> ロジェクトのどこにもネットワーク書き込み経路は存在しません)。
> `gate` は HYDRA-UMC-SDK 自身の本物の `evaluate_job()` を直接呼び出
> し、決してそのゲートの第二の実装ではありません(
> [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) を参照)。
> `certify` は人間が証言した本物のエビデンスを記録しますが、明示的に
> それを本物のハードウェアに対して独立に検証することは**ありません**
> ——それが実機を手にせずには範囲外にとどまる正確な理由については
> [docs/CERTIFICATION.md](docs/CERTIFICATION.md) を参照してください。
> 今日実在する正確なコマンド面については
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

> **誠実性チェック - 今日実際に動くもの:** マニフェストのスキーマ/バリデータ（`schema.py`）、読み取り専用カタログ（`registry.py`、`catalog_server.py`）、SDK 安全ゲート統合（`sdk_gate.py`。実際にインストールされたチェックアウトに対して `HYDRA-UMC-SDK` 自身の本物の `evaluate_job()` を呼び出しており、モックでは決してない）、認証ログ（`certification.py`）、そして CLI（`cli.py`）は本物であり、188件の通過するテストで検証されている（`pytest tests/`。オプションの `[sdk]` エクストラをインストールした場合で、なければそのうち34件はスキップされる）。`certify` は人間が証言したエビデンスを記録するが、それを実際のハードウェアに対して独立に検証することは明示的に行わない - 10個のフィクスチャのどれの背後にも物理的な機械は存在せず、ここにあるどのアダプタも実際のデバイスと本当に通信するために使われたことは一度もない。`catalog`/`serve-catalog` は構造上 GET のみである（`catalog_server.py` には `do_POST`/`do_PUT` が一切ない）。詳細は上記のステータス欄と、これまでに実際に出荷された内容を記す `CHANGELOG.md` を参照。

> **安全性とセキュリティの現状:** このエコシステムは認証された安全システムではありません。ハードウェアの E-STOP 経路、ファームウェアが強制する制限やインターロック、検証済みの動作コマンドはまだありません。ファームウェアイメージは CRC-32 と Ed25519 署名で検査し、リリースビルドは公開済みの開発用鍵を拒否します(リレーの先のツールヘッドと拡張ボードは引き続き URTC のブートローダーを使い、署名ではなく共有鍵の HMAC-SHA256 を使います)。TLS と相互 TLS は任意で、既定では無効です。独自基板はまだ実装も試験もされていません。ここに書かれた内容を人の安全のために頼る前に、[セキュリティベースライン](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)と[脅威モデル](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)をお読みください。

---

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.1.6` |
| 成熟度 | 機能する |
| テスト | 188 (`python -m pytest -q tests`) |
| 技術 | Python 3.11+ / JSON Schema (hand-written structural validator, no jsonschema dependency) / http.server (stdlib-only real read-only catalog endpoint) / HYDRA-UMC-SDK (optional, real safety-gate integration via evaluate_job()) |
| 対象 | 利用者の PC |
| 実機での確認 | まだです：このバージョンについて実機での動作記録はありません |

**移動：** [概要](#-概要) · [アーキテクチャ](#-アーキテクチャ) · [セキュリティと安全](#-セキュリティと安全) · [インターフェース](#-インターフェース) · [設定](#-設定) · [クイックスタート](#-クイックスタート) · [テスト](#-テスト) · [トラブルシューティング](#-トラブルシューティング) · [リポジトリの構成](#-リポジトリの構成) · [関連プロジェクト](#-関連プロジェクト)

## 🚦 プロジェクトの状況

各行はこのリポジトリの一部分で、信号は今日どこまで進んでいるかを示します。計画ではなく、リポジトリが示せるもの（テスト、ビルド、実行）に基づいて書かれています。

🟢 完了・検証済み · 🟡 動作する（既知の制限あり） · 🟠 一部のみ、または未検証 · 🔴 未実装または動作しない

| 領域 | 状態 | ここでの意味 |
|---|---|---|
| ソフトウェア | 🟡 | 主な目的では動作します。足りない点は上の正直さの確認に書かれています |
| テスト | 🟢 | 自動テスト 188 件。変更のたびに実行されます |
| 実機 | 🔴 | まだです：このバージョンについて実機での動作記録はありません |
| ドキュメント | 🟢 | 8 言語の README。変更のたびにマニフェストと照合されます |

## 🎯 概要

現在、あるセル/マシンがどのブリッジを使うかの選択と設定は、多くの実
在するブリッジリポジトリ自身の README、`.env` ファイル、その場しの
ぎのスクリプトに分散しています。HYDRA-UMC-CONNECTOR-HUB は、任意の実
在する外部マシンについて 3 つの問いに答える唯一の場所になることを意
図しています：**どのプロトコルを話すのか、実際に何ができるのか(読み
取り/書き込み/中止、それぞれどのリスクで)、そしてこのエコシステムの
どの既存の実在するプロジェクトが既にそれを実装しているのか？**

このバージョンは、計画された 4 件すべてを 6 つの部分で届けます:

1. **本物で固定された契約** ([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)) -
   このエコシステムの「CONTRATO MINIMO DE
   ADAPTADOR」であり、既にコードで強制されている譲れないルールを持ち
   ます: `write`/`abort` 能力は、自身のリスク、必要な権限、必要なセル
   状態、人による確認の要否、タイムアウトのすべてを宣言しない限り拒否
   されます。
2. **本物の CLI バリデーター** (`hydra-umc-connector-hub validate`) -
   手書きの構造チェック(`jsonschema` 依存なし)であり、すべての実際の
   エラーが責任のあるアダプター/フィールド/能力を正確に名指しします。
3. **10 件の実際のフィクスチャ**、このエコシステムに既に存在する実際
   のブリッジ/プロトコルプロジェクトそれぞれに 1 件ずつ——この契約が
   理論上のものではないという証拠であり、新しいアダプターマニフェスト
   の出発点となるテンプレートです。
4. **本物の読み取り専用カタログ** (`catalog`/`serve-catalog`) - ディ
   レクトリ内の構造的に有効なすべてのマニフェストを発見し、
   `serve-catalog` では本物の GET のみの `http.server` 経由でそれを公
   開します(このプロジェクトのどこにも書き込みルートは存在しません)。
5. **HYDRA-UMC-SDK 安全ゲートとの本物の統合** (`gate`) -
   `write`/`abort` 能力呼び出しは SDK 自身の本物の `evaluate_job()` に
   よってゲートされ、決してそのロジックの第二の実装ではありません。
   [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) を参照してくだ
   さい。
6. **本物の認証記録** (`certify`/`certifications`) - 人間が証言し、
   追記のみの本物の記録であり、アダプター自身の `evidenceSchema` に照
   らして検証されます。エビデンスを本物のハードウェアに対して独立に検
   証することがここで明示的に範囲外にとどまる理由については
   [docs/CERTIFICATION.md](docs/CERTIFICATION.md) を参照してください。

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

このプロジェクトのどこにもデフォルト/無引数の呼び出しも GUI も存在し
ません——完全かつ本物のコマンド面については
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

## 🧩 HYDRA-UMC での役割

**HYDRA-UMC-CONNECTOR-HUB** は、外部の機械がエコシステムにどう接続するかを、どれにも接続せずに記述します。アダプターはマニフェストで、自分が何か、何ができるか（読み取り・書き込み・中止）、どう認証するかを宣言し、ハブはそれを検証して一覧にし、要求された機能を SDK の本物のゲートに通し、誰が何を認証したかを記録します。

## 🏛️ アーキテクチャ

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-CONNECTOR-HUB architecture" width="100%">
</p>

**この作りにした理由**

- **手書きのバリデーターであり、`jsonschema` ではありません。** 納品 1
  自身の契約は十分に小さく(トップレベルフィールド 14 個、1 つのネス
  トされた能力の形)、実際で具体的なエラー文字列を集める単純な Python
  関数の方が、汎用の JSON-Schema バリデーターより単純でありながら、
  より明確な出力を生成します——すべてのメッセージが、汎用的なスキーマ
  パスではなく、責任のある正確なフィールド/インデックスを名指しします。
- **write/abort の安全ルールはドキュメントではなくコードで強制されて
  います。** `schema.py` の `_WRITE_CAPABILITY_REQUIRED_FIELDS` は、そ
  の明示的なルールが本物のテスト済みチェックに変換されたものです
  ——マニフェストの作者がそれを忘れることはできません。忘れた能力をバ
  リデーターが拒否するからです。
- **`authenticationRef` は参照として検証され、自由記述テキストとして
  信頼されることは決してありません。** 実際の接頭辞の閉じた集合
  (`env:`、`secret-store:`、`vault:`、`none:`)——意図的に「秘密っぽ
  く見える」ヒューリスティックではありません(まさに同じ問題に対して
  もヒューリスティックが間違ったツールである理由は、HYDRA-UMC-OPS-
  AGENT 自身の `log_redaction.py` を参照してください)。
- **すべてのエラーが収集され、決して最初の 1 つだけではありません。**
  `validate_adapter_manifest()` は問題を見つけた後も検証を続けます
  ——マニフェストを修正する人は、1 回の実行ですべての実際の問題を目に
  します。
- **カタログは意図的に本物で読み取り専用です。** `registry.py` はディ
  レクトリを非再帰的にスキャンします(そのため入れ子になった
  `fixtures/invalid/` が本物のカタログに加わることは決してありませ
  ん)。`validate_adapter_manifest()` に失敗したものは除外されます
  が、それでも報告され続けます。同じ `adapterId` を宣言する 2 つのフ
  ァイルは、2 番目の方が拒否されます。`catalog_server.py` にはどこに
  も `do_POST`/`do_PUT` がありません——書き込みの試みは、このプロジェ
  クトが保護し忘れたルートではなく、`BaseHTTPRequestHandler` 自身の
  正直な `501` を受け取ります。
- **安全ゲートは HYDRA-UMC-SDK 自身の本物のロジックを再利用し、決して
  その第二の実装ではありません。** `sdk_gate.py` の
  `evaluate_capability_call()` は、すべての `write`/`abort` 能力に対
  して `hydra_umc_sdk.bridge_contract.evaluate_job()` を直接呼び出し
  ます——`read` 能力は決して SDK に触れません。`evaluate_job()` は運
  動/書き込みゲートであり、読み取りゲートではないからです。この統合
  が行う唯一の意図的で明示された単純化(中止以外のあらゆる書き込みに
  単一の代替 `JobPhase` を使うこと)については、
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) を参照してくだ
  さい。
- **認証記録は、自身が何を証明でき何を証明できないかについて正直で
  す。** `certification.py` は、エビデンスがアダプター自身の
  `evidenceSchema` と一致しない認証の保存を拒否しますが、そのエビデ
  ンスが本物のハードウェアから来たことを独立に検証すると主張すること
  は決してありません——このプロジェクトのどこにも、それを確認するた
  めに本物のシリアルポート/OPC-UA セッション/MQTT 接続を開くコードパ
  スはありません。[docs/CERTIFICATION.md](docs/CERTIFICATION.md) を
  参照してください。
- **10 件のフィクスチャは実在する所有者プロジェクトを名指しし、決して
  架空のものではありません。** `fixtures/*.json` の各 `ownerProject`
  は、このエコシステムの実在するリポジトリです(関連プロジェクトの節
  を参照)——これは実際のレジストリテンプレートであり、投機的なもの
  ではありません。
- **コアには標準ライブラリのみを使用します。**
  `validate`/`catalog`/`serve-catalog`/`certify`/`certifications` は
  依存関係を一切必要としません——`json`、構造チェック用の通常の
  Python、そして `http.server` です。`write`/`abort` 能力に対する
  `gate` だけが、オプションの `[sdk]` extra を必要とします。

## 🔒 セキュリティと安全

| 脅威 | 防御 | 場所 |
|---|---|---|
| 他のプロジェクトを装うアダプター | 所有者プロジェクトは `^(HYDRA-UMC\|URTC)(-[A-Z0-9-]+)?$` に一致する必要があり、`--ecosystem-root` を付けるとそのリポジトリの `hydra-umc.project.json` と照合されます | `schema.py`, `cli.py` |
| マニフェスト内の認証情報、巨大なマニフェスト、未知のモード | `authenticationRef` が受け付けるのは `env:`・`secret-store:`・`vault:`・`none:` の接頭辞だけで（秘密そのものは不可）、マニフェストは最大 1 000 000 バイト。機能のモードは `read`・`write`・`abort`、冪等性は `none`・`idempotent`・`at-least-once`・`exactly-once` です | `schema.py` |
| ゲートを通さずにアダプターを呼ぶ、古いリクエスト | `gate` は SDK 自身の `evaluate_job()` を呼び、別の実装は使いません。申告された状態を信用するには `--allow-unobserved` が必要で、マニフェストの求めに応じて `--human-confirmed`・`--safety-gate`・`--permission` も要ります。30 秒より古い、または 5 秒より先のリクエストは拒否されます | `sdk_gate.py`, `cli.py` |
| 改ざんされた認証記録とネットワーク経由の書き込み | 記録は 16 文字以上の鍵で封印されたハッシュチェーンを成し（`.chain-head.json`、`.chain.lock`）、`verify --strict` はチェーン外の記録で失敗します。`catalog` と `serve-catalog` は GET 専用で、プロジェクトのどこにもネットワーク経由の書き込み経路はありません | `ledger.py`, `catalog_server.py` |

**絶対にしないこと：** 機械には一切触れず、認証は人が証明した内容を保存するだけで、証拠が実機に対して検証されることはありません（`docs/CERTIFICATION.md` を参照）。

## 🔌 インターフェース

コマンド `hydra-umc-connector-hub`（または `./run.sh`）。詳しくは `docs/CLI_REFERENCE.md` を参照してください。カタログは HTTP（GET のみ）でも提供され、既定は `127.0.0.1:8801` です。

| トピックまたはルート | 内容 |
|---|---|
| `validate MANIFEST...` | マニフェストを契約に照らして検証 |
| `catalog --registry-dir DIR`, `serve-catalog --registry-dir DIR --port 8801` | アダプターを一覧するか、同じ一覧を GET で提供（`--ecosystem-root` は所有者プロジェクトも検査） |
| `gate MANIFEST --capability ... --job-id ... --idempotency-key ... --source ... --cell-state ... --machine-state ...` | 機能を SDK のゲートに通す（`--param k=v`、`--evidence-file`、`--allow-unobserved`、`--human-confirmed`、`--safety-gate`、`--permission`） |
| `certify`, `certifications`, `verify --strict` | 人の証明をハッシュチェーンに記録し、記録を一覧し、チェーンを検証 |

## ⚙️ 設定

専用の環境変数はありません。レジストリのフォルダー、カタログのホストとポート（`--registry-dir`、`--host`、`--port`）、認証チェーンの鍵（16 文字以上）はコマンドライン引数です。アダプターの認証情報はマニフェストに書かれず、置き場所への参照だけが書かれます。

## 🚀 クイックスタート

Python 3.11 以上が必要です。コアは標準ライブラリだけを使います（追加パッケージ `sdk`、`pip install -e ".[sdk]"` が必要なのは、書き込み・中止の機能に対する `gate` のときだけです）。

```bash
chmod +x build.sh   # 初回のみ
./build.sh          # .venv を作成、pip install -e ".[dev]"、コンパイルチェック + テスト
./run.sh                                   # 本物のデモ: 10 件の実際のフィクスチャを検証
./run.sh validate fixtures/industrial-opcua.json
./run.sh validate fixtures/invalid/*.json  # これらはそれぞれ INVALID を報告するはずです
./run.sh catalog --registry-dir fixtures
./run.sh serve-catalog --registry-dir fixtures --port 8801   # Ctrl+C で停止
pip install -e ".[sdk]"                    # write/abort 能力に対する `gate` にのみ必要
./run.sh gate fixtures/cnc-grbl.json --capability sendControlByte --job-id j1 \
    --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
./run.sh certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "あなたの名前" --evidence-file real-status.json --out-dir certifications/
```

Windows では: 先に `build.bat`、その後 `run.bat`(引数なしの場合は同じ
デモ) / 上記いずれかのサブコマンド。`build-test.sh`/`.bat` は、この
プロジェクト自身の CI が実行するのと同じコンパイルチェック(Python
の構文のみ)を、プロジェクトのバージョンや CHANGELOG に触れずに実行
します——ただしそれ自体はテストスイートを実行しません。CI は
`pytest` を別の、より後のステップとして実行します。完全なローカル
テストスイートには `./build.sh`/`build.bat`(または直接
`pytest tests/`)を実行してください。

**トラブルシューティング**

- `validate` が、正しいと思っているマニフェストに対して `INVALID` を
  報告する: 列挙されたすべての理由を読んでください——バリデーターは
  最初の 1 つだけでなく、すべてを報告します。フィールドごとの正確な
  契約については [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)
  を参照してください。
- `validate` が `ERROR: ... is not valid JSON` を報告する: ファイル自
  体が不正な形式の JSON であり、これは整形式だが無効なマニフェストと
  は別の問題です——契約自体を確認する前に、カンマや引用符の欠落を確
  認してください。
- `catalog`/`serve-catalog` が終了コード `1` になるか、
  `invalidFiles` にファイルが列挙される: そのファイルは構造検証に失
  敗し、意図的にカタログから除外されました——理由の完全な一覧を見る
  には、それに対して直接 `validate` を実行してください。
- `gate` が `ERROR: the optional 'hydra-umc-sdk' package is not
  installed` で失敗する: 先に `pip install -e ".[sdk]"` を実行してく
  ださい——`write`/`abort` 能力にのみ必要です。
- `gate`/`certify` が `ERROR: unknown cell_state ...` または
  `... does not match evidenceSchema` で失敗する: 期待される正確な
  値/形については
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)/
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md) を参照してください。

## 🧪 テスト

`python -m pytest -q tests` で自動テスト 188 件を実行します（うち 39 件は追加パッケージ `sdk` が必要で、なければスキップされます）。スキーマと公開 JSON スキーマ、カタログ、SDK のゲート、認証チェーン、コマンドライン、悪意ある入力が対象で、ハードウェアも外部ネットワークも不要です。

CI は `HYDRA_UMC_CI=1 python tools/ci_validate.py` を実行し、マニフェスト、文書、8 つの README、図を検査します。

## 🏗️ ビルドとリリース

リリースのためにコンパイルするものはありません。`build.sh` / `build.bat` は仮想環境を作り、パッケージを編集可能モードでインストールし、テストを実行します。`build-test` は検査だけです。ビルドでバージョンが変わることはなく、上げるのは `python tools/hydra_project_tool.py bump` だけで、変更履歴も一緒に進めます。パッケージ、マニフェスト、変更履歴のバージョンは一致する必要があり、一致しなければ `ci_validate.py` が失敗します。

## 🩺 トラブルシューティング

| 表示 | 原因 | 対処 |
|---|---|---|
| `INVALID` on a manifest | マニフェストが契約に違反しています（所有者プロジェクトの誤り、`authenticationRef` 内の秘密、未知のモード、1 000 000 バイト超） | `validate` のメッセージを読みます。`./run.sh validate fixtures/invalid/*.json` で全種類の失敗が確認できます |
| `gate` refuses a write or abort capability | SDK が未インストール、状態が観測されていない、またはマニフェストが求める確認が欠けています | `pip install -e ".[sdk]"`。`--observed-machine-state` を与えるか、申告状態を受け入れるなら `--allow-unobserved`。求めに応じて `--human-confirmed`・`--safety-gate`・`--permission` を付けます |
| `verify --strict` fails | 認証記録がハッシュチェーンの外にあるか、鍵が違います | チェーンを封印した鍵（16 文字以上）を使います。手で追加・編集した記録は、設計上チェーンの外になります |

## 📂 リポジトリの構成

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-CONNECTOR-HUB" width="100%">
</p>

<details>
<summary>ツリーのテキスト版</summary>

```text
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py                                アダプターマニフェストの契約と検証器
│   ├── registry.py                              実際のブリッジをアダプターとして登録
│   ├── catalog_server.py                        GET 専用のカタログエンドポイント
│   ├── sdk_gate.py                              SDK 自身の evaluate_job() を呼ぶ
│   ├── certification.py ledger.py               封印されたハッシュチェーンの認証記録
│   └── cli.py                                   validate, catalog, serve-catalog, gate, certify
├── tests/                                       188 件
├── docs/                                        マニフェスト、ゲート、認証、成熟度のガイド
├── fixtures/                                    実際のアダプターマニフェスト 10 件と無効な例
├── schemas/                                     公開された JSON スキーマ
├── tools/                                       ビルド・テスト実行、バージョン引き上げ、CI 検証、README と図の生成・検査
├── images/                                      バナーと README の図
├── .github/                                     CI ワークフローと Issue テンプレート
├── pyproject.toml                               パッケージのメタデータと依存関係
├── hydra-umc.project.json                       マニフェスト：バージョン・成熟度・ファミリー
├── CHANGELOG.md                                 各バージョンの変更点
├── build.sh build.bat                           ビルドスクリプト（バージョンは変えません）
├── build-test.sh build-test.bat                 ビルドスクリプト（バージョンは変えません）
├── test.sh test.bat                             テストを実行
├── bump_version.py / bump_manifest_version.py   明示的なバージョン引き上げ
├── run.sh run.bat                               デモとコマンド
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE LICENSE.md
```

</details>

## 🗺️ ロードマップと既知の制限

**現時点の既知の制限**

このプロジェクト自身のマニフェストと CHANGELOG に名付けられた計画の
4 件すべてが、今や本物でテスト済みのコードを届けています。正直に言
うと、残っているのは:

- **納品 4 のハードウェア検証のギャップは意図的に未解決のままです。**
  `certify` は、アダプター自身の `evidenceSchema` に照らして検証され
  た、人間が証言するエビデンスを記録しますが、このプロジェクトのどこ
  にも、そのエビデンスが実際に指名された実機から来たことを独立に確認
  するものはありません——それには、この開発マシンが持たない、実際の
  セル内の物理的なハードウェアそのものが必要です。
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md) を参照してください。
- **本物のクライアント統合:始まったが、まだ終わっていません。**
  HYDRA-UMC-SERVER は今や本当に `serve-catalog` をポーリングしています
  ——`GET /api/adapters` と `GET /api/adapters/:adapterId` は、このプロ
  ジェクト自身の本物のカタログをエンドツーエンドで中継します(HYDRA-UMC-
  SERVER 自身の `tools/verify_connector_hub_relay_contract.mjs` を参照
  してください。これはこのプロジェクトの本物の `serve-catalog` を、そ
  の本物の `fixtures/` と本物の Server インスタンスに対して起動します
  ——モックでは決してありません)。また、このプロジェクト自身のチェッ
  クアウトの外側の venv に本物の wheel としてインストールし、そこから
  実行することで、パッケージング自体(単なる editable インストールで
  はなく)が機能することも確認しました。Studio/Suite/Updater が自ら
  `gate` を呼び出すことは、依然として本物で別個の、将来の作業です。
- **`gate`/`certify` の呼び出し元と実際のセル/マシンの状態との間の本
  物の転送手段が欠けています。** 今日、`--cell-state`/
  `--machine-state` は既知の値として呼び出し元から与えられます——
  HYDRA-UMC-SERVER や安全ゾーンサービスからそれらをライブで取得する
  コードパスはここにはありません。

## 🌍 言語

この README とリポジトリの文書は、英語・スペイン語・ドイツ語・フランス語・イタリア語・日本語・中国語・ポルトガル語（ポルトガル）の 8 言語で提供されています。8 つのファイルは同時に書かれ、同じ節と同じリンクを持つことを CI が確認します。 このリポジトリには独自の画面もメッセージカタログもないため、翻訳すべきインターフェース文字列はありません。

## 🔗 関連プロジェクト

本プロジェクトは、同じ作者(JuanenRac / Electro Hobby 3D)による HYDRA-UMC ロボティクスエコシステムの一部です。リクエストが実はこの中のどれかについてのものである可能性があるため、知っておく価値があります。

**直接関連**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — すべてのブリッジが既に自身のコマンドを検証している共有 JSON-Schema 契約。本ハブの `gate` コマンド(納品 3)は、write/abort 能力に対してその本物の `bridge_contract.evaluate_job()` を直接呼び出し、決してそのゲートの第二の実装ではありません。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 関連する新プロジェクト: このエコシステム自身のコンポーネントの保守インシデントライフサイクルを運用する一方、本ハブは**外部**のマシン/アダプターが何をできるかを発見し検証します。
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 本プロジェクトによって明示的に置き換えられることはありません: GATEWAY-INDUSTRIAL は独自のコマンド許可リストを持つ実際のプロトコルリレーです。本ハブはそれとすべての他のブリッジの上に位置する宣言的なレジストリ/バリデーターであり、いかなるプロトコルの第二の実装でもありません。

**エコシステムの他のプロジェクト**

*コアハードウェア&プラットフォーム*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — ロボットアームのマザーボードの設計——CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大 8 本のツールアームを統括することを目指す(ファームウェアは初期段階で、実装済みの基板はまだない)。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — CM5 向けの再現可能な Raspberry Pi OS プロダクト層——読み取り専用エージェント、検証済み設定/プロファイル、WiFi 初回接続プロビジョニング。

*コアバックエンド&クライアント*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する、本物のヘッドレスバックエンド(REST/WebSocket)。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット 3D 可視化を備えたウェブ制御ダッシュボード。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 複数のサーバーを同時に扱えるデスクトップ(PySide6)スウォームコマンドセンター。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされた Wear OS コンパニオンを備えたネイティブ Android 制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイム WebSocket 同期を備えた iOS/iPadOS 制御アプリ(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 本体搭載の 7 インチ DSI タッチスクリーン向けネイティブタッチ UI、CM5 自体に組み込み。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルを STUDIO 自身のカタログへ送信するデスクトップ用グラフィカル URDF 作成/編集ツール。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — HYDRA-UMC-EDITOR-URDF も編集する同じモデルカタログ内で、実在するパーツを変換/置換/削除/追加するデスクトップ STL モデルエディタ。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — VDA 5050 MQTT パブリッシャーによる AGV/AMR フリートの調整境界(エミュレートしたフリートに対してのみテスト済み)。本ハブ自身の `mobile-vda5050` フィクスチャの背後にある本物の `ownerProject`。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — GRBL ステータス/制御バイトへのアクセスを持つ、CNC セルの高レベルコーディネーター(エミュレーターに対してのみテスト済み)。本ハブ自身の `cnc-grbl` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Boston Dynamics Spot コマンド送信機能を持つ、脚型/ヒューマノイドドロイドの調整境界(エミュレーターに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — キー/筐体/インターロックの GPIO 信号 3 系統を読み取るレーザーセルのコーディネーター(模擬チップに対してのみテスト済み。レーザーの武装や発射はできない)。本ハブ自身の `laser-safety` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnP ピックアンドプレースの基板フローを安全に統括する高レベルコーディネーター。本ハブ自身の `pnp-openpnp` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際にゲート制御されたジョブコマンドを持つ、Moonraker/Klipper 3D プリンター向けの安全な調整境界。本ハブ自身の `printer-moonraker` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 遅延インポートの rclpy ROS 2 トランスポートを持つコーディネーター(ROS 2 環境ではまだ実行していない)。本ハブ自身の `robotics-ros2` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — MAVLink コマンド送信機能を持つ、カメラ搭載 UAV の調整境界(エミュレーターに対してのみテスト済み)。本ハブ自身の `uav-mavlink` フィクスチャの背後にあるプロジェクト。

*URTC ツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的な Universal Robot Tool Controller 基板向けファームウェア、CAN バス経由の 25 以上のツールプロファイル。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTC 基板用のデスクトップ GUI 書き込みツール、CAN-OTA およびフルチップ SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTC 基板向けのデスクトップ CAN バスライブ診断ツール、ツールプロファイルごとに 1 パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API を使ったブラウザベースの URTC-TESTER の代替、ローカルインストール不要。
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — URTC の CAN バスの前に置くゲートウェイ：許可する識別子のリスト、レート制限、セッション鍵。コンピューター上でテスト済みで、実際のバスではまだ試していません。

*ビジョン AI ノード(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 ビジョンパイプラインの統合ハブ、段階ごとの実際のハードウェア準備状況チェック付き。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailo アーキテクチャ/チェックサムによる安全読み込み検証を備えた、実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際の HailoRT 統合境界を持つ、実際の GStreamer パイプライン + MediaMTX 設定生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ゾーン状態を条件に承認する Position-Based Visual Servoing 補正則。カメラによる姿勢推定はまだない。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — ファイルから物体位置を受け取る、ゾーン侵入・キャリブレーション鮮度・E-STOP 要求の v0 ロジック。検出器は接続されておらず、物理 E-STOP もまだ配線されていない。

*コグニティブ AI ノード(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10 コグニティブパイプライン(LLM/VLA/音声オーケストレーション)の統合ハブ。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Action モデル向けの、実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 確認ゲート付きの限定的な Watch リレーを備えた、実際の音声フロントエンド(VAD + 意図解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCU エラーコードに対する、実際のルールベースのタスク分解と意味的エラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身の Markdown ドキュメントに対する、標準ライブラリのみの実際の TF-IDF 文書検索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — エコシステム自身のための、ローカルでポリシーゲート付きのAIメンテナンス技術者 — 観察、診断し、修正を提案する;最上位の2つのリスクレベルは意図的にまだ実装されていない。

*オーケストレーション&スウォーム*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際の gRPC/Protobuf ヘルスレポート契約とミッションステートマシンを持つ統合ハブ。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際の HTTP API 上に構築された、優先度ベースの実際のジョブキュー(重複排除付き)。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — リトライ/バックオフとアイデンティティ不一致検出を備えた、実際の gRPC ベースのフリートヘルスウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/ワークスペース衝突検証を備えた、実際の RRT ベースの 3D 経路プランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 複数セルの収束についてプロパティテストされた、実際の CRDT LWW-Element-Map 状態同期。

*デジタルツイン&シミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を持つ、デジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実機の間にソフトウェアの衝突インターロックを備えたハードウェア・イン・ザ・ループのルーター(実機なしでテスト済み)。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 実際の URDF サブセットに対する、実際の順運動学と関節限界検証。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — YOLO/COCO アノテーションのエクスポート機能を持つ、実際のプロシージャル 2D シーンジェネレーター。

*データ&分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 実際の取り込み/クエリ HTTP API を備えた、実際の sqlite3 ベースの時系列ストア。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — ドリフト監視を備えた、実際の FFT + 統計ベースラインによる異常検知器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — DATALAKE の履歴に対する実際の OEE/稼働率計算、再現可能な CSV エクスポート付き。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — シーケンス重複排除機能を備えた、DATALAKE への実際の CAN/WebSocket 取り込みパイプライン。

*産業用ゲートウェイ*
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 実際のバイナリプロトコルクライアントセッションで検証された、実際の OPC-UA アドレス空間。本ハブ自身の `industrial-opcua` フィクスチャの背後にある本物の `ownerProject`。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — クライアント単位のオプション認証とトピック ACL を備えた、実際の MQTT ブローカー。本ハブ自身の `industrial-mqtt` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 縮退モード出力を備えた、実際の MTConnect `/probe` および `/current` XML エンドポイント。本ハブ自身の `manufacturing-mtconnect` フィクスチャの背後にあるプロジェクト。

*エコシステム運用*
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — エコシステムのすべてのチェックアウトを検出・インストール・更新する。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — 新しく完全に最新の CM5 イメージを構築する。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 再現可能な開発ホスト（Raspberry Pi 5 / CM5）。エコシステムのソースコードを保管し、永続キューのもとで境界の明確なビルド/テストタスクを実行する。運用中の CM5 とは明確に異なる、開発専用の役割。
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 誠実な統計フォールバックを備えた、DATALAKE/ANOMALY-DETECTOR 上のスマートサマリーと異常ハイライトパネル。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 実際の安定した終了コード契約を持つフリート CLI、HYDRA-UMC-SERVER 自身の API の本物のライブクライアント。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 触覚アラートのパターンとペアリング済みスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ(物理的なウォッチではまだ実行していない)。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際の工具 ID デコードと Smart Idle 予熱ロジックを備えた、基板搭載ラック用ファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB 検査ツールヘッド向けの、ファームウェアと実際の Python ビジョンコンパニオン。

## 📚 ドキュメント

さらに読むには：

* [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md) - アダプターマニフェストの契約（項目ごと）
* [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) - 機能が SDK のゲートを通る仕組み
* [docs/CERTIFICATION.md](docs/CERTIFICATION.md) - 認証記録とは何で、何ではないか
* [docs/MATURITY_CRITERIA.md](docs/MATURITY_CRITERIA.md) - アダプターがより成熟とみなされる条件
* [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) - 全コマンドとオプション（実際の出力付き）
* [エコシステムのセキュリティ基準](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [エコシステムの脅威モデル](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [このリポジトリの変更履歴](CHANGELOG.md)
* [このリポジトリのライセンス](LICENSE.md)

## 🤝 コントリビュートとコミュニティ

* プルリクエストの前に `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（または `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）を実行してください。`CI_VALIDATION=PASS` と表示される必要があります。この確認に `build.sh` や `build.bat` は使わないでください。ビルドは検査ではありません。
* 8 つの README は HYDRA-UMC-DOCS の 1 つのソースから書かれます。手で編集しないでください。ソースを変更し、`tools/make_readmes.py` で書き直します。
* 実行していないことを README に書かないでください。事実であれば「シミュレーションのみ」「実機では未確認」と書きます。
* [CONTRIBUTING.md](CONTRIBUTING.md)、[行動規範](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md)、[SUPPORT.md](SUPPORT.md) を参照してください。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE).
