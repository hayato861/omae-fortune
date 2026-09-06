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
analytics_logger = logging.getLogger("fortune.analytics")
analytics_logger.setLevel(logging.INFO)
ALLOWED_EVENTS = {"fortune_started", "share_started", "share_completed", "premium_clicked", "fortune_helpful", "fortune_missed"}
FULL_WIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
STRIPE_PLANS = {
    "single": {"mode": "payment", "price_env": "STRIPE_SINGLE_PRICE_ID"},
    "monthly": {"mode": "subscription", "price_env": "STRIPE_MONTHLY_PRICE_ID"},
}
CONCERNS = {
    "work": {"label": "仕事", "opening": "働き方の癖は、てめえの鬼の武器と弱点がいちばん露骨に出る場所だ。", "move": "成果を一つに絞り、誰が見ても分かる形で残せ", "avoid": "評価を焦って手柄を独り占めすること"},
    "money": {"label": "銭", "opening": "銭は欲の鏡だ。稼ぎ方より、何に怯えて使うかに性根が出る。", "move": "今月の固定費を一つ見直し、残す金の行き先を先に決めろ", "avoid": "不安を消すためだけの衝動買い"},
    "love": {"label": "恋", "opening": "惚れた相手の前じゃ、強みと弱みは同じ顔で現れやがる。", "move": "察してもらうのをやめ、望みを短い言葉で一つ伝えろ", "avoid": "返事を勝手に想像して先に傷つくこと"},
    "life": {"label": "生き方", "opening": "道に迷うのは、道がねえからじゃない。捨てたくねえ道が多すぎるからだ。", "move": "今後三か月で守るものを一つだけ紙に書け", "avoid": "全部を同時に立て直そうとすること"},
}


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
    fortune = dict(FORTUNES[day_number - 1])
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
        "move": concern_data["move"],
        "avoid": concern_data["avoid"],
        "seven_days": seven_days,
    }


@app.get("/")
def index():
    return render_template("index.html", today=date.today())


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/events")
def track_event():
    payload = request.get_json(silent=True) or {}
    event = payload.get("event")
    if event not in ALLOWED_EVENTS:
        return {"error": "invalid event"}, 400
    analytics_logger.info(json.dumps({"event": event}, ensure_ascii=False))
    return "", 204


@app.post("/fortune")
def fortune():
    name = request.form.get("name", "").strip()[:30]
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
    if not name or not birthday_is_valid:
        return render_template(
            "index.html",
            today=date.today(),
            error="名前と生年月日ぐれえ、しゃんと入れな！",
            name=name,
            birthday=birthday,
            birthday_year=birthday_year,
            birthday_month=birthday_month,
            birthday_day=birthday_day,
        ), 400
    analytics_logger.info(json.dumps({"event": "fortune_completed"}, ensure_ascii=False))
    return render_template(
        "result.html",
        today=date.today(),
        name=name,
        birthday=birthday,
        fortune=daily_fortune(name, birthday),
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
