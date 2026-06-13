# pachinko-close-watcher

[p-johojima.jp の閉店カテゴリ](https://p-johojima.jp/category/close/) を **1日1回** チェックし、
新着記事があれば **Discord** に通知する仕組み。GitHub Actions で動くので **無料・サーバー不要**。

## 仕組み

1. GitHub Actions が毎日 08:00 JST に起動
2. `check_updates.py` がカテゴリのRSSフィードを取得
3. 前回保存した既読URL一覧 (`state.json`) と比較
4. 新着があれば Discord Webhook に通知
5. `state.json` を更新してリポジトリにコミット

外部ライブラリは不要（Python標準ライブラリのみ）。

## セットアップ手順

### 1. Discord Webhook URL を発行
Discordで通知したいチャンネル → **編集（歯車）** → **連携サービス** → **ウェブフック** → **新しいウェブフック** → **ウェブフックURLをコピー**

### 2. GitHub にリポジトリを作成して push
```bash
cd pachinko-close-watcher
git init
git add .
git commit -m "init: pachinko close watcher"
gh repo create pachinko-close-watcher --public --source=. --push
# gh が無ければ GitHub上で手動でリポジトリ作成 → git remote add origin ... → git push
```
> Actions の実行時間を完全無料・無制限にするため **public** を推奨。
> private でも月2,000分の無料枠内で問題なく動きます。

### 3. Webhook URL を GitHub Secret に登録
リポジトリ → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
- Name: `DISCORD_WEBHOOK_URL`
- Secret: コピーしたWebhook URL

### 4. 動作確認（任意）
リポジトリ → **Actions** タブ → **Check p-johojima close updates** → **Run workflow** で手動実行。
- 初回実行は既存記事を「既読」として記録するだけで通知しません（過去記事の大量通知を防ぐため）。
- 2回目以降、新着があった時だけ通知されます。

## ローカルでテストする場合
```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python3 check_updates.py
```
`DISCORD_WEBHOOK_URL` を設定せずに実行すると、通知はスキップして検知結果だけ表示します。

## 注意点
- cron はGitHubの混雑で **数分〜十数分遅れる** ことがあります（即時通知ではありません）。
- スケジュール実行は **リポジトリが60日間無活動だと自動停止** します。新着時の `state.json` コミットで活動が発生するため通常は問題ありませんが、長期間新着がない場合は手動でActionsを再有効化してください。
- 通知間隔やチェック時刻は `.github/workflows/check.yml` の `cron` で変更できます（例: `0 */6 * * *` で6時間ごと）。
