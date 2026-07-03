# Sales KPI Command Center

営業・SaaS の主要 KPI を一覧し、異常値と次の確認ポイントを示すダッシュボード。
MRR・Churn・Conversion Rate を中心に、月次推移と閾値アラートで“どこを見直すべきか”を可視化する。

## 目的

KPI 設計とドリルダウンのやり方を示す、公開用の小型アプリ。
複数の KPI を一画面で俯瞰し、閾値を超えた項目をアラートで際立たせることで、
数値の羅列ではなく“次の一手”が伝わる構成にしている。

## 主要機能

- **KPI Overview**: 最新月の MRR / 顧客数 / Churn rate / Conversion（won/leads）と MRR・Churn の推移
- **Funnel**: 指定月の Leads → MQL → SQL → Won ファネルと段階別変換率、月次ファネル表
- **Revenue Trend**: 月次 MRR と MoM 成長率
- **Churn**: 月次解約顧客数と Churn rate 推移
- **Alerts**: 閾値超過を CRITICAL / WARNING / INFO の3段階で表示、アラート・タイムライン
- **データ差替え**: サイドバーから合成データの再生成、または CSV アップロードで差し替え
- **閾値の調整**: サイドバーのスライダーで Churn / MRR drop / Conversion の閾値を変更（アラートに即反映）
- **空データ耐性**: データ未選択・空 CSV でも説明メッセージを表示し落ちない

## 使用技術

- Python 3.11+
- Streamlit（UI）
- Plotly（グラフ）
- pandas / numpy（集計）
- pytest / ruff（テスト・Lint）

## データの出所

**すべて合成データであり、実在企業の数値ではない。**
`src/data.py` の `generate_synthetic_data()` が乱数で月次 KPI を生成する。
実在企業の規模感や実績を模倣せず、明示的に架空の数値範囲を使っている。
アラート機能の確認用に、意図的に異常月（チャーン急増・MRR急減）が2つ仕込まれている。

サンプル CSV: `data/sample_kpis.csv`（合成データ24ヶ月分）。

### CSV スキーマ

列は以下の9つ。数値列は非負、`month` は `YYYY-MM` 文字列。

```
month, mrr, customers, new_customers, churned_customers,
leads, qualified_leads, opportunities, won_deals
```

- `mrr`: 月次経常収益（USD）
- `customers`: 月末顧客数
- `new_customers` / `churned_customers`: 当月の新規獲得 / 解約
- `leads` → `qualified_leads`(MQL) → `opportunities`(SQL) → `won_deals`: ファネル各段階

欠損列は 0 で補完、負値は 0 にクリップ、不正な数値は 0 扱いで安全に読み込む。

## ローカル実行手順

```bash
cd sales-kpi-command-center

# 仮想環境を作成して依存をインストール
uv venv --python 3.11 .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt # または: pip install -r requirements.txt

# 起動
streamlit run app/streamlit_app.py
```

ブラウザが開かなければ http://localhost:8501 を開く。

### テスト・Lint

```bash
pytest            # src/ の集計・アラート関数（42件）
ruff check src app tests
```

### 環境変数・APIキー

**不要。** 本アプリはキーなしで動く。外部APIも呼ばない。

## スクショ置き場

画面截图は `assets/` に配置する（Overview / Funnel / Revenue / Churn / Alerts）。

## 制限事項

- MVP 範囲: 認証・DB・本番運用機能・課金・複雑な状態管理ライブラリは含まない
- データはメモリ上のみ。永続化しない
- 合成データのため、ビジネス判断の根拠としては使えない
- チャーン率は `churned_customers / customers`（月末残ベースの簡易指標）。厳密な期間定義ではない
- ファネル段階名（MQL/SQL）は一般的な呼称を使うダミー区分

## ディレクトリ構成

```
sales-kpi-command-center/
├── app/streamlit_app.py   # エントリポイント（UIは薄く）
├── src/                   # 集計・閾値判定ロジック（UI非依存）
│   ├── data.py            # 合成データ生成・CSV読込・検証
│   ├── metrics.py         # MRR/Churn/サマリー/MoM
│   ├── alerts.py          # 閾値アラート
│   └── funnel.py          # ファネル・変換率
├── tests/                 # pytest（src/ の純関数を検証）
├── data/sample_kpis.csv   # サンプルCSV
├── assets/                # スクショ置き場
└── requirements.txt
```
