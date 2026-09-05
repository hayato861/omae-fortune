# お前のためだけの占い

「やれるもんならやってみろ、嘘はつくじゃねえ！」を掲げ、人ならざる鬼・百烈鬼がお前のためだけに今日の運勢を見抜く、Flask製の占いサイトMVPです。生年月日から数秘タイプを計算し、日替わり運勢を重ねます。

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

個人情報やCookieを使わず、`fortune_started`、`fortune_completed`、`share_started`、`share_completed`、`premium_clicked` のイベント名だけをRenderログへ出力します。結果画面の共有ボタンは、氏名と生年月日を含まない鬼印PNGをブラウザー内で生成します。

## 有料化について

現在の極み版ページは価格と特典を検証するための画面で、決済は発生しません。本番化では Stripe Checkout などをサーバー側で接続してください。
