<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b></p>

### 🧩 外部マシン用アダプターのための宣言的レジストリとバリデーター

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only core">
  <img src="https://img.shields.io/badge/Deliveries-4%20of%204-367BF5.svg" alt="4 件中 4 件の納品完了">
</p>

> **ステータス: v0.0.6、scaffolding - 4 件の納品のうち全 4 件(スキー
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

---

## 1. 🛠️ 技術概要

現在、あるセル/マシンがどのブリッジを使うかの選択と設定は、多くの実
在するブリッジリポジトリ自身の README、`.env` ファイル、その場しの
ぎのスクリプトに分散しています。HYDRA-UMC-CONNECTOR-HUB は、任意の実
在する外部マシンについて 3 つの問いに答える唯一の場所になることを意
図しています：**どのプロトコルを話すのか、実際に何ができるのか(読み
取り/書き込み/中止、それぞれどのリスクで)、そしてこのエコシステムの
どの既存の実在するプロジェクトが既にそれを実装しているのか？**

このバージョンは、その計画の 4 件すべてを届けます:

1. **本物で固定された契約** ([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)) -
   エコシステム全体のソフトウェア改善監査自身の「CONTRATO MINIMO DE
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

$ hydra-umc-connector-hub gate fixtures/cnc-grbl.json --capability sendControlByte \
    --job-id j1 --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
{"allowed": true, "reason": "cell and external machine are ready", "evidenceErrors": []}

$ hydra-umc-connector-hub certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Juan Enrique" --evidence-file real-status.json --out-dir certifications/
CERTIFIED adapterId='cnc-grbl' certificationId='...' -> certifications/cnc-grbl__....json
```

このプロジェクトのどこにもデフォルト/無引数の呼び出しも GUI も存在し
ません——完全かつ本物のコマンド面については
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

## 2. 🧱 アーキテクチャと設計上の決定

- **手書きのバリデーターであり、`jsonschema` ではありません。** 納品 1
  自身の契約は十分に小さく(トップレベルフィールド 14 個、1 つのネス
  トされた能力の形)、実際で具体的なエラー文字列を集める単純な Python
  関数の方が、汎用の JSON-Schema バリデーターより単純でありながら、
  より明確な出力を生成します——すべてのメッセージが、汎用的なスキーマ
  パスではなく、責任のある正確なフィールド/インデックスを名指しします。
- **write/abort の安全ルールはドキュメントではなくコードで強制されて
  います。** `schema.py` の `_WRITE_CAPABILITY_REQUIRED_FIELDS` は、監
  査自身の明示的な文が本物のテスト済みチェックに変換されたものです
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

## 📂 リポジトリ構成

```
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py            # 本物の adapter-manifest 契約 + 構造バリデーター + JSON-Schema サブセットチェッカー
│   ├── registry.py          # 納品 2: ディレクトリを本物で安定してソートされたカタログにスキャン
│   ├── catalog_server.py    # 納品 2: カタログを公開する本物の GET のみの http.server
│   ├── sdk_gate.py          # 納品 3: HYDRA-UMC-SDK evaluate_job() との本物の統合
│   ├── certification.py     # 納品 4: 人間が証言する、追記のみの本物の認証記録
│   └── cli.py               # validate/catalog/serve-catalog/gate/certify/certifications エントリーポイント
├── fixtures/                # 10 件の本物で有効なアダプターマニフェスト(既存の各ブリッジに 1 件)
│   └── invalid/             # 5 件の本物で無効なマニフェスト、それぞれが 1 つの拒否理由を示す
├── tests/                   # 本物のテスト: フィクスチャ、一時的なポート上の本物の http.server、実際にインストールされた hydra-umc-sdk、一時ディレクトリ内の本物の認証記録
├── docs/
│   ├── ADAPTER_MANIFEST.md  # 完全な本物の契約、フィールドごとの説明
│   ├── CAPABILITY_GATE.md   # 納品 3 自身の本物のゲート契約とその唯一の明示された単純化
│   ├── CERTIFICATION.md     # 納品 4 自身の本物の契約とその正直なハードウェア検証のギャップ
│   └── CLI_REFERENCE.md     # すべてのサブコマンド、その出力形、終了コード契約
├── images/                  # メディアとアプリアイコン
├── tools/
│   ├── build_test.py        # バージョン管理を伴わないビルド/コンパイルチェック
│   └── ci_validate.py       # CI が使用するマニフェスト/CHANGELOG/ドキュメントの検証
├── build.sh / build.bat     # venv + 編集可能インストール + コンパイルチェック + テスト
├── build-test.sh / .bat     # 何も変更しない、ビルド検証のみ
├── run.sh / run.bat         # 本物のデモ: 10 件のフィクスチャを検証(引数なしの場合)、または本物の CLI コマンドを転送
├── bump_version.py          # エコシステム全体の「走行距離計」式インクリメント(pyproject.toml + __init__.py)
└── bump_manifest_version.py # hydra-umc.project.json のバージョンをネイティブのものと同期(--sync)
```

## ⚙️ ビルドと実行

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

## 🚀 ロードマップ

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

## 🔗 関連プロジェクト

本プロジェクトは、同じ作者(JuanenRac / Electro Hobby 3D)による HYDRA-UMC ロボティクスエコシステムの一部です。リクエストが実はこの中のどれかについてのものである可能性があるため、知っておく価値があります。

**直接関連**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — すべてのブリッジが既に自身のコマンドを検証している共有 JSON-Schema 契約。本ハブの `gate` コマンド(納品 3)は、write/abort 能力に対してその本物の `bridge_contract.evaluate_job()` を直接呼び出し、決してそのゲートの第二の実装ではありません。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 監査提案が推奨するもう一つの新プロジェクト: このエコシステム自身のコンポーネントの保守インシデントライフサイクルを運用する一方、本ハブは**外部**のマシン/アダプターが何をできるかを発見し検証します。
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 本プロジェクトによって明示的に置き換えられることはありません: GATEWAY-INDUSTRIAL は独自のコマンド許可リストを持つ実際のプロトコルリレーです。本ハブはそれとすべての他のブリッジの上に位置する宣言的なレジストリ/バリデーターであり、いかなるプロトコルの第二の実装でもありません。

**エコシステムの他のプロジェクト**

*コアハードウェア&プラットフォーム*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 実際のロボットアームのマザーボード——CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大 8 本のツールアームを統括。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — CM5 向けの再現可能な Raspberry Pi OS プロダクト層——読み取り専用エージェント、検証済み設定/プロファイル、WiFi 初回接続プロビジョニング。

*コアバックエンド&クライアント*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する、本物のヘッドレスバックエンド(REST/WebSocket)。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット 3D 可視化を備えたウェブ制御ダッシュボード。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 複数のサーバーを同時に扱えるデスクトップ(PySide6)スウォームコマンドセンター。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされた Wear OS コンパニオンを備えたネイティブ Android 制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイム WebSocket 同期を備えた iOS/iPadOS 制御アプリ(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 本体搭載の 7 インチ DSI タッチスクリーン向けネイティブタッチ UI、CM5 自体に組み込み。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルを STUDIO 自身のカタログへ送信するデスクトップ用グラフィカル URDF 作成/編集ツール。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 実際の VDA 5050 MQTT パブリッシャーによる AGV/AMR フリートの調整境界。本ハブ自身の `mobile-vda5050` フィクスチャの背後にある本物の `ownerProject`。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 実際の GRBL ステータス/制御バイトへのアクセスを持つ、CNC セルの高レベルコーディネーター。本ハブ自身の `cnc-grbl` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 実際の Boston Dynamics Spot コマンド送信機能を持つ、脚型/ヒューマノイドドロイドの調整境界。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 実際のキー/筐体/インターロック GPIO セーフガード 3 系統を読み取る、レーザーセルの安全コーディネーター。本ハブ自身の `laser-safety` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnP ピックアンドプレースの基板フローを安全に統括する高レベルコーディネーター。本ハブ自身の `pnp-openpnp` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際にゲート制御されたジョブコマンドを持つ、Moonraker/Klipper 3D プリンター向けの安全な調整境界。本ハブ自身の `printer-moonraker` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 実際の遅延インポート rclpy ROS 2 トランスポートを持つ安全コーディネーター。本ハブ自身の `robotics-ros2` フィクスチャの背後にあるプロジェクト。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 実際の MAVLink コマンド送信機能を持つ、カメラ搭載 UAV の調整境界。本ハブ自身の `uav-mavlink` フィクスチャの背後にあるプロジェクト。

*URTC ツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的な Universal Robot Tool Controller 基板向けファームウェア、CAN バス経由の 25 以上のツールプロファイル。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTC 基板用のデスクトップ GUI 書き込みツール、CAN-OTA およびフルチップ SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTC 基板向けのデスクトップ CAN バスライブ診断ツール、ツールプロファイルごとに 1 パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API を使ったブラウザベースの URTC-TESTER の代替、ローカルインストール不要。

*ビジョン AI ノード(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 ビジョンパイプラインの統合ハブ、段階ごとの実際のハードウェア準備状況チェック付き。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailo アーキテクチャ/チェックサムによる安全読み込み検証を備えた、実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際の HailoRT 統合境界を持つ、実際の GStreamer パイプライン + MediaMTX 設定生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 上流のゾーン状態に応じて安全ゲート制御される、実際の Position-Based Visual Servoing 補正則。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — キャリブレーションの鮮度を強制する、実際のゾーン侵入チェックと E-STOP 要求。

*コグニティブ AI ノード(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10 コグニティブパイプライン(LLM/VLA/音声オーケストレーション)の統合ハブ。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Action モデル向けの、実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 確認ゲート付きの限定的な Watch リレーを備えた、実際の音声フロントエンド(VAD + 意図解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCU エラーコードに対する、実際のルールベースのタスク分解と意味的エラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身の Markdown ドキュメントに対する、標準ライブラリのみの実際の TF-IDF 文書検索。

*オーケストレーション&スウォーム*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際の gRPC/Protobuf ヘルスレポート契約とミッションステートマシンを持つ統合ハブ。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際の HTTP API 上に構築された、優先度ベースの実際のジョブキュー(重複排除付き)。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — リトライ/バックオフとアイデンティティ不一致検出を備えた、実際の gRPC ベースのフリートヘルスウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/ワークスペース衝突検証を備えた、実際の RRT ベースの 3D 経路プランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 複数セルの収束についてプロパティテストされた、実際の CRDT LWW-Element-Map 状態同期。

*デジタルツイン&シミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を持つ、デジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実際のハードウェアの間でコマンドをルーティングする、実際のハードウェア・イン・ザ・ループ安全インターロック。
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
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 誠実な統計フォールバックを備えた、DATALAKE/ANOMALY-DETECTOR 上のスマートサマリーと異常ハイライトパネル。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 実際の安定した終了コード契約を持つフリート CLI、HYDRA-UMC-SERVER 自身の API の本物のライブクライアント。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 実際の触覚アラートとペアリングされたスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際の工具 ID デコードと Smart Idle 予熱ロジックを備えた、基板搭載ラック用ファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB 検査ツールヘッド向けの、ファームウェアと実際の Python ビジョンコンパニオン。

---

## 📚 ドキュメント & コミュニティ

- **[docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)** — 完全な本物の契約、フィールドごとの説明、そしてなぜ `authenticationRef` が参照でなければならないのか。
- **[docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)** — 納品 3 自身の HYDRA-UMC-SDK 安全ゲートとの本物の統合と、その唯一の明示された単純化。
- **[docs/CERTIFICATION.md](docs/CERTIFICATION.md)** — 納品 4 自身の本物の認証記録契約と、その正直なハードウェア検証のギャップ。
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — すべてのサブコマンド、その出力形、終了コード契約。
- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— プルリクエストのための技術スタックとコーディング指針。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** —— このコミュニティで期待される行動規範。
- **[SECURITY.md](SECURITY.md)** —— 脆弱性の報告方法と、このプロジェクトの実際のセキュリティ重点領域。
- **[SUPPORT.md](SUPPORT.md)** —— 質問の投稿先とバグの報告先。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 ライセンス

GPL-3.0(ソフトウェア)/ CC BY-SA 4.0(ドキュメント)—— 詳細は [LICENSE.md](LICENSE.md) を参照してください。
