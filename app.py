from __future__ import annotations

import hashlib
import base64
import json
import logging
import os
import random
from datetime import date, timedelta

from flask import Flask, redirect, render_template, request, url_for
import stripe
from cryptography.fernet import Fernet, InvalidToken


app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600
analytics_logger = logging.getLogger("fortune.analytics")
analytics_logger.setLevel(logging.INFO)
if not analytics_logger.handlers:
    analytics_handler = logging.StreamHandler()
    analytics_handler.setFormatter(logging.Formatter("%(message)s"))
    analytics_logger.addHandler(analytics_handler)
analytics_logger.propagate = False
ALLOWED_EVENTS = {"fortune_started", "share_started", "share_completed", "premium_clicked", "fortune_helpful", "fortune_missed"}
ALLOWED_EVENTS.update({"page_view", "landing_view", "pages_fortune_completed"})
FULL_WIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
STRIPE_PLANS = {
    "single": {"mode": "payment", "price_env": "STRIPE_SINGLE_PRICE_ID"},
    "monthly": {"mode": "subscription", "price_env": "STRIPE_MONTHLY_PRICE_ID"},
}
CONCERNS = {
    "work": {"label": "仕事", "opening": "働き方の癖は、てめえの鬼の武器と弱点がいちばん露骨に出る場所だ。", "move": "成果を一つに絞り、誰が見ても分かる形で残せ", "avoid": "評価を焦って手柄を独り占めすること", "moves": ["成果を一つに絞り、誰が見ても分かる形で残せ", "抱えた仕事を一つ見せて、具体的な助言をもらえ", "今週やらねえ仕事を一つ決め、本命に時間を渡せ"], "avoids": ["評価を焦って手柄を独り占めすること", "曖昧なまま引き受け、あとで一人で抱え込むこと", "忙しさを勲章にして、順番を失うこと"]},
    "money": {"label": "銭", "opening": "銭は欲の鏡だ。稼ぎ方より、何に怯えて使うかに性根が出る。", "move": "今月の固定費を一つ見直し、残す金の行き先を先に決めろ", "avoid": "不安を消すためだけの衝動買い", "moves": ["今月の固定費を一つ見直し、残す金の行き先を先に決めろ", "買う前に三つ比べ、値段より長く使えるかで決めろ", "小さな漏れを一つ止め、その分を先取りで残せ"], "avoids": ["不安を消すためだけの衝動買い", "人に見栄を張るための分不相応な出費", "安さだけを理由に、いらねえ物を増やすこと"]},
    "love": {"label": "恋", "opening": "惚れた相手の前じゃ、強みと弱みは同じ顔で現れやがる。", "move": "察してもらうのをやめ、望みを短い言葉で一つ伝えろ", "avoid": "返事を勝手に想像して先に傷つくこと", "moves": ["察してもらうのをやめ、望みを短い言葉で一つ伝えろ", "会いたいなら候補日を二つ出して、相手に選ばせろ", "相手の話を最後まで聞き、急いで結論を奪うな"], "avoids": ["返事を勝手に想像して先に傷つくこと", "昔の相手や誰かと比べて、今の縁を測ること", "試すような言い方で、本音を隠すこと"]},
    "life": {"label": "生き方", "opening": "道に迷うのは、道がねえからじゃない。捨てたくねえ道が多すぎるからだ。", "move": "今後三か月で守るものを一つだけ紙に書け", "avoid": "全部を同時に立て直そうとすること", "moves": ["今後三か月で守るものを一つだけ紙に書け", "明日の自分を楽にする小さな習慣を一つ始めろ", "役目を終えた予定か物を一つ手放し、余白を作れ"], "avoids": ["全部を同時に立て直そうとすること", "人の正解を借りて、自分の本音を後回しにすること", "疲れを無視して、根性だけで押し切ること"]},
}

HEXAGRAM_NAMES = (
    "乾為天", "坤為地", "水雷屯", "山水蒙", "水天需", "天水訟", "地水師", "水地比",
    "風天小畜", "天澤履", "地天泰", "天地否", "天火同人", "火天大有", "地山謙", "雷地豫",
    "澤雷隨", "山風蠱", "地澤臨", "風地観", "火雷噬嗑", "山火賁", "山地剝", "地雷復",
    "天雷无妄", "山天大畜", "山雷頤", "澤風大過", "坎為水", "離為火", "澤山咸", "雷風恒",
    "天山遯", "雷天大壮", "火地晋", "地火明夷", "風火家人", "火澤睽", "水山蹇", "雷水解",
    "山澤損", "風雷益", "澤天夬", "天風姤", "澤地萃", "地風升", "澤水困", "水風井",
    "澤火革", "火風鼎", "震為雷", "艮為山", "風山漸", "雷澤帰妹", "雷火豊", "火山旅",
    "巽為風", "兌為澤", "風水渙", "水澤節", "風澤中孚", "雷山小過", "水火既済", "火水未済",
)
HEXAGRAM_GUIDANCE = (
    ("てめえの前に道はある。まず腹を決めて一歩出ろ。", "最初の一手を今日中に打て", "考えすぎて出発を遅らせること"),
    ("おい小便小僧、今は育てる時だ。土を耕さず実を急ぐな。", "小さな習慣を一つ続けろ", "結果を急いで根っこを抜くこと"),
    ("べらんめえ、まだ動くな。潮目を読んだ奴が最後に笑う。", "情報を一つ集めてから決めろ", "焦って大勝負に出ること"),
    ("人の手を借りろ。ひとりで賢いふりをするのは今日で終いだ。", "信頼できる相手に相談しろ", "黙ったまま察してもらうこと"),
    ("減らせ。空いた場所がねえと、新しい運は入ってこねえ。", "役目を終えた物か予定を一つ手放せ", "全部を抱えたまま走ること"),
    ("増やすなら筋を通せ。小さな一手が、あとで大きな流れになる。", "誰かに価値を一つ返せ", "見返りだけを先に数えること"),
    ("火がついてやがる。だが燃え尽きるまで走るのは馬鹿のやることだ。", "熱いうちに一つ完成させろ", "勢いで約束を増やすこと"),
    ("終わりは負けじゃねえ。畳むからこそ、次の勝負へ行ける。", "今日終わらせる一件を決めろ", "古い話を何度も裁き直すこと"),
)
HEXAGRAM_STAGES = (
    ("初爻・仕込み", "まだ土台だ。おい小便小僧、でけえ話は後にして足元を固めな。"),
    ("二爻・伸び始め", "芽は出てやがる。べらんめえ、ここで人の手を借りりゃ伸びるぞ。"),
    ("三爻・転換前", "調子に乗ると転ぶ場所だ。勢いは残して、手順だけは守りやがれ。"),
    ("四爻・外へ出る", "内輪の準備は終いだ。てめえの仕事を表へ出して、反応を受けな。"),
    ("五爻・要所", "ここが勝負どころだ。欲張らず、一番大事な一手に腹を決めろ。"),
    ("上爻・締めくくり", "頂上で浮かれるな。終わらせ方まで決めた奴が、次の道を取る。"),
)


def normalize_digits(value: str) -> str:
    return value.translate(FULL_WIDTH_DIGITS)


def payment_cipher() -> Fernet | None:
    secret = os.getenv("PAYMENT_DATA_KEY", "")
    if len(secret) < 32:
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_reading_data(name: str, birthday: str, concern: str) -> str:
    cipher = payment_cipher()
    if not cipher:
        raise RuntimeError("PAYMENT_DATA_KEY is not configured")
    payload = json.dumps({"name": name, "birthday": birthday, "concern": concern}, ensure_ascii=False, separators=(",", ":"))
    return cipher.encrypt(payload.encode("utf-8")).decode("ascii")


def decrypt_reading_data(token: str) -> dict[str, str] | None:
    cipher = payment_cipher()
    if not cipher or not token:
        return None
    try:
        return json.loads(cipher.decrypt(token.encode("ascii")).decode("utf-8"))
    except (InvalidToken, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def checkout_is_paid(checkout) -> bool:
    return checkout.status == "complete" and checkout.payment_status in {"paid", "no_payment_required"}


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


FORTUNES = [
    {
        "rank": "大吉",
        "score": 96,
        "headline": "てめえの出番だ、腹ァ決めな！",
        "message": "今日は遠慮がいちばんの貧乏くじだ。先に名乗って、先に動け。筋を通した強引さなら、運のほうからついてきやがる。",
        "work": "面倒な一件を午前中に片づけろ。評価はあとから追いつく。",
        "money": "小銭を惜しんで時間を捨てるな。道具への投資は吉だ。",
        "love": "格好つけずに、短い本音をひとつ言え。",
        "action": "長く放置している連絡を一本返す",
        "color": "勝負赤",
    },
    {
        "rank": "吉",
        "score": 82,
        "headline": "おい小便小僧、今日は足で稼ぎな！",
        "message": "頭ん中でこね回しても答えは出ねえ日だ。現場を見て、人に会って、手を動かせ。三歩目あたりで景色が変わるぜ。",
        "work": "相談は早いほど得。五分の確認が半日の手戻りを救う。",
        "money": "見栄の出費に注意。腹と仕事に効く金なら惜しむな。",
        "love": "気の利いた台詞より、約束の時間を守れ。",
        "action": "昼休みに10分だけ外を歩く",
        "color": "鉄紺",
    },
    {
        "rank": "中吉",
        "score": 74,
        "headline": "悪かねえ。だが浮かれて財布を落とすなよ",
        "message": "追い風は吹いてるが、帆を張りすぎりゃ船がひっくり返る。今日は七分の力で丁寧に仕上げるのが粋ってもんだ。",
        "work": "新規より仕上げ。未完了を一つ閉じると流れが来る。",
        "money": "勢い買いは一晩寝かせろ。固定費の見直しは大当たり。",
        "love": "相手の話を最後まで聞け。それだけで株が上がる。",
        "action": "机か鞄を一か所だけ片づける",
        "color": "山吹",
    },
    {
        "rank": "小吉",
        "score": 63,
        "headline": "地味を笑うな、地味が最後に銭を持ってくる",
        "message": "派手な当たりはねえが、足場を固めるには上等な日だ。約束、睡眠、帳尻。この三つを守りゃ明日のてめえが礼を言う。",
        "work": "数字と期限を再確認。見落としを拾えば勝ちだ。",
        "money": "財布の紐は並。使途不明の支出を一つ止めろ。",
        "love": "無理に盛り上げるな。気楽な相づちが効く。",
        "action": "今夜はいつもより30分早く寝る",
        "color": "利休鼠",
    },
    {
        "rank": "末吉",
        "score": 51,
        "headline": "焦るな若造、潮目は夕方に変わる",
        "message": "朝から噛み合わなくても腐るんじゃねえ。余計な勝負を避けて、来た球だけ打て。夕方には小さな拾い物がある。",
        "work": "即答するな。大事な返事は一度下書きに置け。",
        "money": "貸し借りと大口の契約は今日は見送るのが無難。",
        "love": "昔の話を蒸し返すな。今日の機嫌は今日で直せ。",
        "action": "温かいものを食って深呼吸を三回",
        "color": "深緑",
    },
    {"rank": "吉", "score": 79, "headline": "人の縁を侮るな、答えは向こうから歩いてくる", "message": "一人で片をつけるより、今日は人の知恵を借りたほうが早え。雑談の中に、止まっていた話を動かす鍵が紛れているぜ。", "work": "抱えた仕事を一つ見せろ。思わぬ助言が入る日だ。", "money": "共同購入や比較検討が吉。ひとりの勢いで決めるな。", "love": "用事がなくても声をかけろ。短いやり取りが縁を温める。", "action": "しばらく話していない相手へ一言送る", "color": "藤紫"},
    {"rank": "中吉", "score": 71, "headline": "捨てる覚悟が、新しい席を空ける日だ", "message": "増やすばかりが前進じゃねえ。役目を終えた物、古い段取り、惰性の約束を一つ切れ。空いた場所に運が入り込む。", "work": "やらない仕事を一つ決めろ。大事な一件の精度が上がる。", "money": "使っていない契約を確認しな。小さな漏れを止める好機だ。", "love": "決めつけを捨てて、今の相手を見ろ。昔の採点表は役に立たねえ。", "action": "不要な物か予定を一つ手放す", "color": "墨黒"},
    {"rank": "大吉", "score": 91, "headline": "仕込みは済んだ。今日は表へ打って出ろ", "message": "温めてきたもんを人目にさらす日だ。完璧じゃなくて構わねえ。見せて、聞いて、直す奴にだけ次の扉が開く。", "work": "企画や成果を共有しろ。反応を受けた分だけ完成へ近づく。", "money": "稼ぐための提案に追い風。値段と条件は堂々と口にしな。", "love": "遠回しはやめろ。会いたいなら、具体的な日時を出せ。", "action": "未完成でも一度、人に見せる", "color": "金茶"},
    {"rank": "小吉", "score": 58, "headline": "止まるのも技だ。今日は足元の音を聞け", "message": "無理に流れを作ろうとすると空回りする。観察して、整えて、次の一手を小さく試せ。静かな日ほど本音がよく聞こえる。", "work": "結論より情報集め。見落とした条件を拾えば明日が楽になる。", "money": "大きく動かすな。残高と今月の予定を眺めるだけで十分だ。", "love": "沈黙を悪く取るな。相手にも考える間を渡してやれ。", "action": "予定を15分空けて何もしない", "color": "白銀"},
    # Each personal day has three distinct readings. The variant is selected
    # deterministically from the name, birthday, and target date.
    {"rank": "大吉", "score": 94, "headline": "先陣を切れ。今日はてめえの声が道を開く", "message": "待ってりゃ誰かが決めると思うな。最初の一言を出した奴に、今日の流れは味方する。", "work": "会議の冒頭で結論を置け。話が早くなる。", "money": "必要な道具は今日そろえると後で効く。", "love": "誘うなら理由を飾らず、会いたいと言え。", "action": "朝いちばんに今日の目的を一行で書く", "color": "朱赤"},
    {"rank": "大吉", "score": 89, "headline": "扉は開いてる。手を伸ばすのを怖がるな", "message": "準備はもう足りてる。迷いを消すのは考えじゃなく、試しに動いた実感だ。", "work": "眠らせた案を一人に見せろ。返事が次を運ぶ。", "money": "値下げより、価値を説明するほうを選べ。", "love": "好意は匂わせず、短くまっすぐ渡せ。", "action": "後回しの申し込みを一つ送る", "color": "紅梅"},
    {"rank": "吉", "score": 80, "headline": "足を運べ。答えは机の外で待ってやがる", "message": "考え込むほど遠くなる日だ。見に行き、聞きに行き、手を動かせば筋が見える。", "work": "現場か担当者へ直接確認しろ。", "money": "比較表を作れば、余計な出費が消える。", "love": "文字だけで決めつけず、声を聞け。", "action": "10分だけ場所を変えて作業する", "color": "青磁"},
    {"rank": "吉", "score": 77, "headline": "小さな移動が、でけえ流れを呼ぶ", "message": "一気に変えなくていい。いつもと違う一手を差し込めば、停滞していた話が動き出す。", "work": "順番を入れ替えて一番重い仕事から片づけろ。", "money": "使う日を決めてから買うと外れねえ。", "love": "いつもと違う話題を一つ出せ。", "action": "新しい店か道を一つ試す", "color": "空色"},
    {"rank": "中吉", "score": 72, "headline": "丁寧さが、派手な一発を追い越す日だ", "message": "急いで見せるより、抜けを一つ潰せ。地味な確認があとでてめえを守る。", "work": "送信前に数字と宛先を二度見ろ。", "money": "契約やサブスクの更新日を確認しな。", "love": "相手の言葉を一度受け止めてから返せ。", "action": "提出物を一つだけ見直す", "color": "砂金"},
    {"rank": "小吉", "score": 66, "headline": "急がば回れだ。整えた奴から明日を取る", "message": "今日は速さより順序がものを言う。散らかったまま走り出すと、同じ場所を回る羽目になる。", "work": "タスクを三つに絞ってから始めろ。", "money": "財布と口座を一度だけ整理しな。", "love": "返事を急かさず、次の約束だけ決めろ。", "action": "机の上を五分だけ整える", "color": "灰青"},
    {"rank": "末吉", "score": 54, "headline": "今日は守りでいい。崩れなきゃ勝ちだ", "message": "調子が出ねえ日に無理な勝負はいらねえ。余計な傷を避ければ、明日また踏み込める。", "work": "重要な返事は夕方まで寝かせろ。", "money": "大きな買い物と貸し借りは見送れ。", "love": "結論を急がず、相手の様子を見ろ。", "action": "予定を一つ減らして体力を残す", "color": "薄墨"},
    {"rank": "吉", "score": 78, "headline": "縁を結べ。ひとりで抱えるのは今日で終いだ", "message": "手を借りるのは負けじゃねえ。頼み方を覚えた奴から、仕事も運も太くなる。", "work": "得意な奴へ具体的に一つ頼め。", "money": "詳しい人の意見を聞いてから決めろ。", "love": "相手にしてほしいことを一つ伝えろ。", "action": "誰かに相談を一件持ちかける", "color": "若草"},
    {"rank": "中吉", "score": 69, "headline": "余白を作れ。運は詰め込みすぎた袋に入らねえ", "message": "足すより空ける日だ。ひとつ手放せば、思いがけねえ声が聞こえてくる。", "work": "会議と予定の間を15分空けろ。", "money": "使っていないサービスを一つ解約しな。", "love": "答えを出さずに一緒に過ごす時間を作れ。", "action": "通知を一時間切る", "color": "薄紫"},
    {"rank": "大吉", "score": 90, "headline": "見せてみな。磨くのは出したあとでも遅くねえ", "message": "完成を待つ奴は、永遠に客席だ。今日のてめえを表へ出せば、次の材料が手に入る。", "work": "成果を共有し、反応を一つもらえ。", "money": "提案の金額を曖昧にするな。", "love": "好きなところを具体的に一つ伝えろ。", "action": "未完成の案を人に見せる", "color": "黄金"},
    {"rank": "吉", "score": 83, "headline": "追い風だ。遠慮の帆をたたむんじゃねえ", "message": "今までの仕込みが、ようやく人の目に届く日だ。堂々と名乗れば話が早い。", "work": "自分の役割と成果を言葉にしろ。", "money": "条件交渉は今日なら強気でいい。", "love": "会いたい日を二つ候補に出せ。", "action": "自分から発表か提案を一つする", "color": "金茶"},
    {"rank": "小吉", "score": 60, "headline": "止まって見えりゃ、深く潜ってるだけだ", "message": "表の動きが鈍い日は、裏側を整える好機だ。焦って水面をかき回すな。", "work": "資料の根拠を一つ補強しろ。", "money": "残高と来月の予定を紙に書け。", "love": "返事の間を悪意と決めつけるな。", "action": "ひとりで考える時間を20分取る", "color": "月白"},
    {"rank": "小吉", "score": 57, "headline": "静けさを味方につけろ。今日は耳が先だ", "message": "喋るほど答えが逃げる日もある。聞いて、観察して、最後に一言だけ決めろ。", "work": "相手の要望をメモしてから提案しろ。", "money": "広告や口コミを鵜呑みにするな。", "love": "相手の話を遮らず最後まで聞け。", "action": "スマホを置いて温かい飲み物を飲む", "color": "夜藍"},
    {"rank": "末吉", "score": 52, "headline": "疲れを実力と勘違いするな。今日は戻れ", "message": "踏ん張るだけが強さじゃねえ。整えて戻る判断が、次の勝負を長くする。", "work": "締切の再交渉は早めに伝えろ。", "money": "ストレス買いを一晩止めろ。", "love": "機嫌が悪いまま大事な話をするな。", "action": "いつもより早く灯りを消す", "color": "藍鼠"},
    {"rank": "吉", "score": 76, "headline": "切り替えろ。古い地図じゃ今日の道は読めねえ", "message": "昨日のやり方に礼を言って、今日は一つ新しく試せ。変化は敵じゃなく道具だ。", "work": "手順かツールを一つ入れ替えろ。", "money": "別の店や方法を比べてから払え。", "love": "過去の失敗を今日の相手に重ねるな。", "action": "初めての方法で一件片づける", "color": "橙"},
    {"rank": "中吉", "score": 73, "headline": "遊び心を戻せ。固い拳じゃ運はつかめねえ", "message": "正解ばかり探すと、面白い抜け道を見落とす。少し笑える方へ舵を切れ。", "work": "企画に一つだけ意外な案を混ぜろ。", "money": "長く使える楽しみへの出費は吉だ。", "love": "気の利いた冗談より一緒に笑える話をしろ。", "action": "気になっていた場所へ寄り道する", "color": "柿色"},
    {"rank": "小吉", "score": 64, "headline": "ひと区切りつけろ。残したままじゃ次へ行けねえ", "message": "全部を救おうとするな。今日終わらせる一つを選べば、胸の奥に風が通る。", "work": "未完了を一件だけ閉じろ。", "money": "未払いと返却物を片づけろ。", "love": "言いそびれた礼を今日伝えろ。", "action": "終わった項目を三つ消す", "color": "枯茶"},
    {"rank": "中吉", "score": 70, "headline": "手放した分だけ、次の景色が見えてくる", "message": "終わりは敗北じゃねえ。役目を終えたものへ礼を言えば、次の縁を迎える場所が空く。", "work": "古い資料を一つ整理して、次の計画を置け。", "money": "眠っているポイントや返金を確認しな。", "love": "過去の連絡先を眺める前に、今日を楽しめ。", "action": "明日のために一つだけ荷物を減らす", "color": "銀鼠"},
]

DAY_DETAILS = {
    1: {"focus": "開始と決断", "social": "先に結論を言うと話が通る。命令口調だけは封じろ。", "body": "頭が先走りやすい。肩と顎の力を抜け。", "best_time": "午前9時〜11時", "caution": "返事を待たずに走り出すこと"},
    2: {"focus": "協力と調整", "social": "相手の言葉を一度言い換えて返せ。誤解がほどける。", "body": "冷えを溜めるな。温かい飲み物が味方だ。", "best_time": "午後2時〜4時", "caution": "遠慮を同意に見せること"},
    3: {"focus": "表現と交流", "social": "面白がる姿勢が人を呼ぶ。自慢話は半分で切り上げろ。", "body": "喉と目を休ませろ。画面から離れる時間を作れ。", "best_time": "正午〜午後2時", "caution": "話を広げすぎて約束を忘れること"},
    4: {"focus": "整理と土台固め", "social": "曖昧な約束を日時と担当に落とせ。信用が積み上がる。", "body": "腰と脚を動かせ。短い散歩でも効く。", "best_time": "午前8時〜10時", "caution": "正しさに固執して手段を変えないこと"},
    5: {"focus": "変化と挑戦", "social": "普段話さねえ相手に縁がある。軽口の後の一言は丁寧にな。", "body": "刺激物と夜更かしは控えめに。勢いの反動が出やすい。", "best_time": "午後3時〜5時", "caution": "飽きた勢いで大事な物まで捨てること"},
    6: {"focus": "責任と愛情", "social": "世話を焼く前に必要か聞け。それだけで親切が真っすぐ届く。", "body": "胃をいたわれ。急いで食うな。", "best_time": "午後5時〜7時", "caution": "他人の問題まで背負い込むこと"},
    7: {"focus": "内省と見極め", "social": "大勢より信頼できる一人と話せ。浅い相づちより本音が効く。", "body": "神経を休ませる静かな時間を確保しろ。", "best_time": "午後8時〜10時", "caution": "考えを隠したまま理解を求めること"},
    8: {"focus": "成果と交渉", "social": "数字と条件をはっきり出せ。筋を通せば強気で構わねえ。", "body": "緊張を溜めやすい。背中を伸ばして深く息を吐け。", "best_time": "午前10時〜正午", "caution": "勝つことに夢中で協力者を雑に扱うこと"},
    9: {"focus": "完了と手放し", "social": "昔の貸し借りを清算しろ。礼か謝罪のどちらかを言葉にしな。", "body": "疲れが表へ出る日だ。風呂と睡眠を削るな。", "best_time": "午後6時〜8時", "caution": "終わった話を何度も裁き直すこと"},
}

LIFE_PATHS = {
    1: {"name": "一閃鬼", "role": "先陣を切る開拓者", "reading": "決める速さは天下一品。てめえが旗を立てりゃ、止まってた話も動き出す。", "weapon": "決断力と突破力", "weakness": "助けまで蹴飛ばす独断", "person": "冷静に反対意見を言える年上", "hell": "独走地獄", "escape": "決める前に一人だけ意見を聞け", "match": "岩城鬼", "clash": "覇道鬼"},
    2: {"name": "双月鬼", "role": "人をつなぐ調停者", "reading": "空気を読む目は鋭い。敵同士だって、てめえが間に立ちゃ話が通る。", "weapon": "共感力と交渉力", "weakness": "嫌われまいと本音を隠す", "person": "決断が速く背中を押してくれる同僚", "hell": "他人軸地獄", "escape": "今日は一度、自分の希望から口にしな", "match": "護炎鬼", "clash": "疾風鬼"},
    3: {"name": "火遊鬼", "role": "場を動かす表現者", "reading": "面白えと思った瞬間の爆発力が武器だ。沈んだ場にも火を入れられる。", "weapon": "発想力と愛嬌", "weakness": "始めるだけで満足する", "person": "話を具体策に変えてくれる実務家", "hell": "散らかし地獄", "escape": "新しいことより、手元の一つを完成させろ", "match": "疾風鬼", "clash": "岩城鬼"},
    4: {"name": "岩城鬼", "role": "崩れぬ土台の職人", "reading": "地道を積み上げる根性がある。最後に信用と銭を持ってくのは、こういう鬼だ。", "weapon": "継続力と堅実さ", "weakness": "変化まで敵扱いする頑固さ", "person": "新しい道具を教えてくれる若手", "hell": "現状維持地獄", "escape": "いつもの手順を一つだけ変えてみな", "match": "一閃鬼", "clash": "火遊鬼"},
    5: {"name": "疾風鬼", "role": "自由を食らう冒険者", "reading": "変化の匂いを嗅ぐ鼻が利く。誰も見てねえ道に、一番乗りできる野郎だ。", "weapon": "適応力と行動速度", "weakness": "飽きたら責任ごと逃げる", "person": "約束を守る堅実な友人", "hell": "飽き逃げ地獄", "escape": "次へ行く前に、残した約束を一つ片づけろ", "match": "火遊鬼", "clash": "双月鬼"},
    6: {"name": "護炎鬼", "role": "情に厚い守り手", "reading": "面倒見の良さは本物だ。てめえがいるだけで、腹を決められる奴がいる。", "weapon": "責任感と育てる力", "weakness": "頼まれてもいねえ荷物を背負う", "person": "遠慮なく弱音を吐ける昔馴染み", "hell": "抱え込み地獄", "escape": "一つ断れ。それは薄情じゃなく整理だ", "match": "双月鬼", "clash": "天灯鬼"},
    7: {"name": "深淵鬼", "role": "本質を射抜く探究者", "reading": "一人で考え抜く力がある。表面の景気のいい話じゃ、てめえの眼はごまかせねえ。", "weapon": "洞察力と専門性", "weakness": "黙ったまま察してもらおうとする", "person": "雑談に連れ出してくれる陽気な奴", "hell": "考えすぎ地獄", "escape": "六割の答えで一度、人に話してみな", "match": "雷眼鬼", "clash": "火遊鬼"},
    8: {"name": "覇道鬼", "role": "成果を奪る勝負師", "reading": "銭と責任を動かす器がある。大勝負ほど目が据わる、生まれつきの大将鬼だ。", "weapon": "統率力と結果への執念", "weakness": "勝ち急いで信頼を置き去る", "person": "耳の痛い数字を見せてくれる参謀", "hell": "勝ち急ぎ地獄", "escape": "成果の前に、協力者へ礼を一つ返せ", "match": "岩城鬼", "clash": "一閃鬼"},
    9: {"name": "万華鬼", "role": "大局を見る理想家", "reading": "でけえ絵を描き、人の事情まで見渡せる。修羅場の最後に道を示す鬼だ。", "weapon": "包容力と俯瞰する目", "weakness": "終わった話まで抱え続ける", "person": "過去より次の予定を話す新人", "hell": "過去執着地獄", "escape": "もう役目を終えた物を一つ手放せ", "match": "天灯鬼", "clash": "覇道鬼"},
    11: {"name": "雷眼鬼", "role": "直感で先を読む伝令者", "reading": "人より先に気配を拾う雷の眼を持つ。まだ言葉にならねえ兆しが見えている。", "weapon": "直感とひらめき", "weakness": "刺激を拾いすぎて消耗する", "person": "話を黙って最後まで聞く落ち着いた人", "hell": "神経すり減らし地獄", "escape": "通知を一時間切って、感じたことを書け", "match": "深淵鬼", "clash": "疾風鬼"},
    22: {"name": "鬼造鬼", "role": "構想を現実にする建築者", "reading": "大仕事を地上へ降ろせる規格外だ。夢物語に柱を立てる腕を持っている。", "weapon": "構想力と実行力", "weakness": "完璧な時を待って動けない", "person": "小さく試すのが得意な現場人", "hell": "完璧主義地獄", "escape": "完成を待つな。今日一本だけ杭を打て", "match": "一閃鬼", "clash": "雷眼鬼"},
    33: {"name": "天灯鬼", "role": "人を照らす規格外の世話人", "reading": "人を救い、場を明るくするでけえ灯を持つ。だが燃料は無限じゃねえぞ。", "weapon": "慈愛と人を奮い立たせる力", "weakness": "自分を空にしてまで尽くす", "person": "てめえ自身を気遣ってくれる家族や相棒", "hell": "自己犠牲地獄", "escape": "今日は誰かでなく、自分のために時間を使え", "match": "万華鬼", "clash": "護炎鬼"},
}

ONI_ASPECTS = (
    {"name": "刃ノ相", "title": "決断に宿る鬼", "gift": "迷いを断ち、最短の一手を選ぶ", "trap": "答えを急ぎ、人の心まで切り捨てる"},
    {"name": "鎧ノ相", "title": "守りに宿る鬼", "gift": "崩れぬ備えで仲間と暮らしを守る", "trap": "傷つかぬことを優先し、好機まで閉め出す"},
    {"name": "炎ノ相", "title": "情熱に宿る鬼", "gift": "熱で人を巻き込み、止まった物事を動かす", "trap": "燃え上がった勢いで約束と体力を使い切る"},
    {"name": "影ノ相", "title": "知略に宿る鬼", "gift": "裏側を読み、誰も見ていない勝ち筋を拾う", "trap": "疑いすぎて、差し出された手まで避ける"},
    {"name": "王ノ相", "title": "器に宿る鬼", "gift": "人と責任を束ね、でかい結果を引き受ける", "trap": "弱みを隠し、一人で王座に取り残される"},
)


def life_path_number(birthday: str) -> int:
    digits = [int(char) for char in birthday if char.isdigit()]
    if len(digits) != 8:
        raise ValueError("invalid birthday")
    total = sum(digits)
    while total not in {11, 22, 33} and total > 9:
        total = sum(int(char) for char in str(total))
    return total


def premium_oni_type(name: str, birthday: str) -> dict[str, str]:
    """無料の12守護鬼を、名前由来の五相で60種類に細分化する。"""
    number = life_path_number(birthday)
    digest = hashlib.sha256(f"oni-aspect:{name.strip()}:{birthday}".encode("utf-8")).digest()
    aspect = ONI_ASPECTS[digest[0] % len(ONI_ASPECTS)]
    base = LIFE_PATHS[number]
    return {
        "full_name": f"{base['name']}・{aspect['name']}",
        "aspect": aspect["name"],
        "title": aspect["title"],
        "gift": aspect["gift"],
        "trap": aspect["trap"],
        "match": base["match"],
        "clash": base["clash"],
    }


def hexagram_reading(name: str, birthday: str, concern: str, target_date: date | None = None) -> dict[str, str | int]:
    target_date = target_date or date.today()
    seed = hashlib.sha256(f"hex:{target_date.isoformat()}:{name.strip()}:{birthday}:{concern}".encode("utf-8")).digest()
    index = int.from_bytes(seed[:4], "big") % len(HEXAGRAM_NAMES)
    line_index = seed[4] % len(HEXAGRAM_STAGES)
    voice, move, avoid = HEXAGRAM_GUIDANCE[index % len(HEXAGRAM_GUIDANCE)]
    line_name, line_voice = HEXAGRAM_STAGES[line_index]
    return {"name": HEXAGRAM_NAMES[index], "index": index + 1, "line": line_index + 1, "line_name": line_name, "voice": f"{voice} {line_voice}", "move": move, "avoid": avoid}


def reduce_number(value: int) -> int:
    while value > 9:
        value = sum(int(char) for char in str(value))
    return value


def personal_day_number(birthday: str, target_date: date) -> int:
    born = date.fromisoformat(birthday)
    personal_year = reduce_number(born.month + born.day + sum(int(c) for c in str(target_date.year)))
    personal_month = reduce_number(personal_year + target_date.month)
    return reduce_number(personal_month + target_date.day)


def daily_fortune(name: str, birthday: str, target_date: date | None = None) -> dict[str, object]:
    target_date = target_date or date.today()
    seed_text = f"{target_date.isoformat()}:{name.strip()}:{birthday}"
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    day_number = personal_day_number(birthday, target_date)
    variant = int(digest[16:24], 16) % 3
    fortune = dict(FORTUNES[(day_number - 1) * 3 + variant])
    fortune["score"] = max(40, min(98, fortune["score"] + rng.randint(-4, 4)))
    fortune["rank"] = "大吉" if fortune["score"] >= 88 else "吉" if fortune["score"] >= 76 else "中吉" if fortune["score"] >= 66 else "小吉" if fortune["score"] >= 56 else "末吉"
    fortune["lucky_number"] = rng.randint(1, 99)
    number = life_path_number(birthday)
    oni_type = LIFE_PATHS[number]
    fortune.update(life_path=number, **oni_type)
    fortune.update(personal_day=day_number, **DAY_DETAILS[day_number])
    fortune["personal_reason"] = f"生来の『{oni_type['weapon']}』に、今日は「{DAY_DETAILS[day_number]['focus']}」の気が重なる。"
    fortune["premium_type"] = premium_oni_type(name, birthday)
    return fortune


def premium_report(name: str, birthday: str, concern: str, target_date: date | None = None) -> dict[str, object]:
    target_date = target_date or date.today()
    concern_data = CONCERNS.get(concern, CONCERNS["life"])
    concern_variant = int(hashlib.sha256(f"concern:{target_date.isoformat()}:{name.strip()}:{birthday}:{concern}".encode("utf-8")).hexdigest()[:8], 16) % 3
    hexagram = hexagram_reading(name, birthday, concern, target_date)
    oni = LIFE_PATHS[life_path_number(birthday)]
    complete = premium_oni_type(name, birthday)
    seven_days = []
    for offset in range(7):
        day = target_date + timedelta(days=offset)
        reading = daily_fortune(name, birthday, day)
        seven_days.append({
            "date": day,
            "focus": reading["focus"],
            "action": reading["action"],
            "score": reading["score"],
        })
    return {
        **complete,
        "base_name": oni["name"],
        "role": oni["role"],
        "reading": oni["reading"],
        "weapon": oni["weapon"],
        "weakness": oni["weakness"],
        "hell": oni["hell"],
        "escape": oni["escape"],
        "concern": concern_data,
        "verdict": f"『{complete['gift']}』が、てめえの突破口だ。ただし『{complete['trap']}』へ落ちれば、持ち味がそのまま仇になる。",
        "move": concern_data["moves"][concern_variant],
        "avoid": concern_data["avoids"][concern_variant],
        "concern_variant": concern_variant,
        "hexagram": hexagram,
        "seven_days": seven_days,
    }


@app.get("/")
def index():
    return render_template("index.html", today=date.today(), concerns=CONCERNS, concern="life")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/events")
def track_event():
    # sendBeacon uses text/plain to avoid a cross-origin preflight on Pages.
    try:
        payload = json.loads(request.get_data())
    except (ValueError, UnicodeDecodeError):
        return {"error": "invalid event"}, 400
    if not isinstance(payload, dict):
        return {"error": "invalid event"}, 400
    event = payload.get("event")
    if not isinstance(event, str) or event not in ALLOWED_EVENTS:
        return {"error": "invalid event"}, 400
    analytics_logger.info(json.dumps({"event": event}, ensure_ascii=False))
    return "", 204


@app.post("/fortune")
def fortune():
    name = request.form.get("name", "").strip()[:30]
    concern = request.form.get("concern", "life")
    birthday_year = normalize_digits(request.form.get("birthday_year", "").strip())
    birthday_month = normalize_digits(request.form.get("birthday_month", "").strip())
    birthday_day = normalize_digits(request.form.get("birthday_day", "").strip())
    birthday = request.form.get("birthday", "")
    if birthday_year or birthday_month or birthday_day:
        birthday = f"{birthday_year}-{birthday_month.zfill(2)}-{birthday_day.zfill(2)}"
    try:
        birthday_is_valid = date.fromisoformat(birthday) <= date.today()
    except ValueError:
        birthday_is_valid = False
    if not name or not birthday_is_valid or concern not in CONCERNS:
        return render_template(
            "index.html",
            today=date.today(),
            error="名前と生年月日ぐれえ、しゃんと入れな！",
            name=name,
            birthday=birthday,
            birthday_year=birthday_year,
            birthday_month=birthday_month,
            birthday_day=birthday_day,
            concern=concern,
            concerns=CONCERNS,
        ), 400
    analytics_logger.info(json.dumps({"event": "fortune_completed"}, ensure_ascii=False))
    fortune_result = daily_fortune(name, birthday)
    report = premium_report(name, birthday, concern)
    fortune_result.update(
        concern=report["concern"],
        concern_key=concern,
        concern_move=report["move"],
        concern_avoid=report["avoid"],
        seven_days=report["seven_days"],
        hexagram=report["hexagram"],
    )
    return render_template(
        "result.html",
        today=date.today(),
        name=name,
        birthday=birthday,
        fortune=fortune_result,
    )


@app.get("/fortune")
def fortune_entry():
    return redirect(url_for("index"), code=303)


@app.get("/premium")
def premium():
    return render_template(
        "premium.html",
        oni_count=len(LIFE_PATHS) * len(ONI_ASPECTS),
        aspects=ONI_ASPECTS,
        stripe_configured=bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_SINGLE_PRICE_ID") and payment_cipher()),
    )


@app.post("/checkout/<plan>")
def create_checkout(plan: str):
    plan_config = STRIPE_PLANS.get(plan)
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    price_id = os.getenv(plan_config["price_env"]) if plan_config else None
    if not plan_config or not secret_key or not price_id:
        return render_template(
            "premium.html",
            oni_count=len(LIFE_PATHS) * len(ONI_ASPECTS),
            aspects=ONI_ASPECTS,
            stripe_configured=False,
            payment_error="決済口を仕込んでいる最中だ。もう少し待ちな！",
        ), 503

    base_url = os.getenv("APP_BASE_URL", request.url_root.rstrip("/"))
    client = stripe.StripeClient(secret_key, max_network_retries=2)
    checkout = client.v1.checkout.sessions.create({
        "mode": plan_config["mode"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{base_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base_url}/premium",
        "allow_promotion_codes": False,
    })
    analytics_logger.info(json.dumps({"event": "checkout_started", "plan": plan}, ensure_ascii=False))
    return redirect(checkout.url, code=303)


@app.get("/checkout/success")
def checkout_success():
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    session_id = request.args.get("session_id", "")
    if not secret_key or not session_id.startswith("cs_"):
        return redirect(url_for("premium"), code=303)
    client = stripe.StripeClient(secret_key, max_network_retries=2)
    checkout = client.v1.checkout.sessions.retrieve(session_id)
    if not checkout_is_paid(checkout):
        return render_template("payment_pending.html"), 402
    encrypted = checkout.metadata.get("reading_data") if checkout.metadata else None
    if encrypted and decrypt_reading_data(encrypted):
        return redirect(url_for("recover_premium_report", session_id=session_id), code=303)
    return render_template("payment_success.html", session_id=session_id, concerns=CONCERNS, customer_email=checkout.customer_details.email if checkout.customer_details else None)


@app.post("/premium/report")
def paid_premium_report():
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    session_id = request.form.get("session_id", "")
    if not secret_key or not session_id.startswith("cs_"):
        return redirect(url_for("premium"), code=303)
    client = stripe.StripeClient(secret_key, max_network_retries=2)
    checkout = client.v1.checkout.sessions.retrieve(session_id)
    if not checkout_is_paid(checkout):
        return render_template("payment_pending.html"), 402
    name = request.form.get("name", "").strip()[:30]
    birthday = normalize_digits(request.form.get("birthday", "").strip())
    concern = request.form.get("concern", "life")
    try:
        birthday_is_valid = date.fromisoformat(birthday) <= date.today()
    except ValueError:
        birthday_is_valid = False
    if not name or not birthday_is_valid or concern not in CONCERNS:
        return render_template("payment_success.html", session_id=session_id, concerns=CONCERNS, error="名前、生年月日、悩みをしゃんと入れな！"), 400
    encrypted = encrypt_reading_data(name, birthday, concern)
    client.v1.checkout.sessions.update(session_id, {"metadata": {"reading_data": encrypted, "reading_saved": "true"}})
    return redirect(url_for("recover_premium_report", session_id=session_id), code=303)


@app.get("/premium/report/<session_id>")
def recover_premium_report(session_id: str):
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    if not secret_key or not session_id.startswith("cs_"):
        return redirect(url_for("premium"), code=303)
    client = stripe.StripeClient(secret_key, max_network_retries=2)
    checkout = client.v1.checkout.sessions.retrieve(session_id)
    encrypted = checkout.metadata.get("reading_data") if checkout.metadata else None
    data = decrypt_reading_data(encrypted)
    if not checkout_is_paid(checkout) or not data:
        return redirect(url_for("checkout_success", session_id=session_id), code=303)
    report = premium_report(data["name"], data["birthday"], data["concern"])
    return render_template("premium_result.html", name=data["name"], report=report, recovery_url=request.url)


@app.post("/stripe/webhook")
def stripe_webhook():
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        return "webhook not configured", 503
    try:
        event = stripe.Webhook.construct_event(request.get_data(), request.headers.get("Stripe-Signature", ""), secret)
    except (ValueError, stripe.SignatureVerificationError):
        return "invalid webhook", 400
    if event["type"] in {"checkout.session.completed", "invoice.paid", "customer.subscription.deleted"}:
        analytics_logger.info(json.dumps({"event": "stripe_event", "type": event["type"]}, ensure_ascii=False))
    return "", 204


if __name__ == "__main__":
    app.run(debug=True)
