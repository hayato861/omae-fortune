# お前のためだけの占い

「やれるもんならやってみろ、嘘はつくじゃねえ！」を掲げ、名を持たぬ鬼がお前のためだけに今日の運勢を見抜く、Flask製の占いサイトMVPです。生年月日から数秘タイプを計算し、日替わり運勢を重ねます。

鑑定結果では12種類の守護鬼から「鬼の武器」「鬼の弱点」「ラッキーパーソン」「気をつけるべき地獄」「地獄を避ける一手」を表示し、スマートフォンの共有機能から鬼印を知らせられます。

有料版は12守護鬼を「刃・鎧・炎・影・王」の五相に分けた全60種類です。同じ守護鬼でも、名前と生年月日の組み合わせから異なる完全鬼名を一意に算出します。

## 起動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

`http://127.0.0.1:5000` を開いてください。

## キャラクター画像の差し替え

初期公開版は、親しみやすさを優先した女鬼の `static/hyakuretsuki-v2.webp` を使用しています。`v3` と `v4` は将来の比較候補です。

## Render へ公開

このリポジトリをGitHubへpushし、RenderでBlueprintとして接続してください。`render.yaml` にビルド、起動、ヘルスチェックの設定が入っています。

公開環境では Gunicorn が `app:app` を起動し、`/healthz` を死活監視に使用します。

## 初期反応の計測

個人情報やCookieを送信せず、イベント名だけをRenderログへ出力します。`page_view` は各ページの表示回数（PV）、`landing_view` は鑑定入口の表示回数です。人数ではなく、再読み込みも1回として数えます。`pages_fortune_completed` はGitHub Pages内で鑑定結果の生成・表示に成功した回数で、結果ページへの直接アクセスや入力のない再読み込みは含みません。サーバー側の `fortune_completed` と合わせて鑑定完了数を集計します。

鑑定開始・共有・極み版クリックも記録します。氏名・生年月日・URL・識別IDは計測データに含めません。結果画面の共有ボタンは、氏名と生年月日を含まない鬼印PNGをブラウザー内で生成します。

直近24時間の反応は次のコマンドで集計できます。Render CLIへのログインが必要です。

```bash
python analytics_report.py
```

期間を変える場合は `python analytics_report.py --hours 168` のように指定します。
稼働確認ログを除外して取得し、1,000件を超える場合も続きのログを取得します。鑑定完了率の分母は鑑定入口表示回数です。計測開始前、Renderの保存期限外、ブラウザーによる送信失敗・遮断分は含まれません。

計測のテストは `python -m pytest -q` と、静的ページ生成後の `node --test tests/test_tracking.cjs` で実行できます。

## 有料化について

Stripe Checkoutの一回払い・月額払い、決済結果確認、署名付きWebhookの受信口を実装しています。鍵が未設定の環境では購入ボタンが無効になります。

Renderには `STRIPE_SECRET_KEY` と `STRIPE_WEBHOOK_SECRET` を秘密の環境変数として設定します。価格IDと公開URLは `render.yaml` に定義済みです。Webhook URLは `https://omae-fortune.onrender.com/stripe/webhook` とし、少なくとも `checkout.session.completed`、`invoice.paid`、`customer.subscription.deleted` を購読してください。テスト用と本番用の鍵・価格IDを混在させないでください。

購入済み鑑定の復元には `PAYMENT_DATA_KEY` も必要です。32文字以上のランダムな秘密値を設定してください。鑑定入力はこの鍵で暗号化してStripe Checkout Sessionのmetadataへ保存し、専用URLから同じ結果を復元します。鍵を変更すると既存の鑑定を復号できなくなるため、運用開始後は変更しないでください。
