# Stock Signal Checker

保有株式の売却タイミングを移動平均線で分析し、Slackに通知するCLIツール。

## 機能

- 日本株の株価データを自動取得（Stooq.com経由）
- 移動平均線（5日/25日）によるテクニカル分析
- ゴールデンクロス/デッドクロスの検出
- Slack Webhookによる通知

## 必要環境

- Python 3.10以上

## セットアップ

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd stock-signal-checker
```

### 2. 仮想環境の作成と有効化

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

```bash
cp .env.example .env
```

`.env` ファイルを編集し、Slack Webhook URLを設定：

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXXX/XXXXX/XXXXX
```

### 5. 保有株式の設定

`config/portfolio.yaml` を編集して、保有銘柄を設定：

```yaml
settings:
  short_period: 5   # 短期移動平均（日）
  long_period: 25   # 長期移動平均（日）

stocks:
  - code: "7203.T"
    name: "トヨタ自動車"
    purchase_price: 2500
    quantity: 100
```

## 使い方

### 基本実行

```bash
python src/main.py
```

### オプション

| オプション | 説明 |
|-----------|------|
| `-v, --verbose` | 詳細出力モード |
| `--dry-run` | Slack通知せずに結果を表示のみ |
| `--no-slack` | Slack通知を無効化 |
| `--sell-only` | 売りシグナル検出時のみ通知 |
| `-c, --config` | 設定ファイルのパスを指定 |

### 実行例

```bash
# 結果を表示のみ（Slack通知なし）
python src/main.py --dry-run

# 詳細表示モード
python src/main.py -v

# 売りシグナルがある時のみ通知
python src/main.py --sell-only
```

## シグナルの判定基準

### デッドクロス（売りシグナル）

短期移動平均線（5日）が長期移動平均線（25日）を上から下に抜けた場合

### ゴールデンクロス（買いシグナル）

短期移動平均線（5日）が長期移動平均線（25日）を下から上に抜けた場合

## Slack通知の設定

1. [Slack API](https://api.slack.com/messaging/webhooks) でIncoming Webhookを作成
2. 取得したWebhook URLを `.env` ファイルに設定

## プロジェクト構成

```
stock-signal-checker/
├── config/
│   └── portfolio.yaml      # 保有株式の設定
├── src/
│   ├── __init__.py
│   ├── main.py             # エントリーポイント
│   ├── stock_fetcher.py    # 株価データ取得
│   ├── analyzer.py         # テクニカル分析
│   └── notifier.py         # Slack通知
├── .env.example            # 環境変数テンプレート
├── .gitignore
├── requirements.txt
└── README.md
```

## 定期実行の設定（オプション）

### macOS (launchd)

`~/Library/LaunchAgents/com.stock-signal-checker.plist` を作成：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stock-signal-checker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/stock-signal-checker/venv/bin/python</string>
        <string>/path/to/stock-signal-checker/src/main.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/path/to/stock-signal-checker</string>
</dict>
</plist>
```

登録：

```bash
launchctl load ~/Library/LaunchAgents/com.stock-signal-checker.plist
```

### Linux (cron)

```bash
crontab -e
```

以下を追加（毎日18時に実行）：

```
0 18 * * 1-5 cd /path/to/stock-signal-checker && ./venv/bin/python src/main.py
```

## ライセンス

MIT
