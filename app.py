from __future__ import annotations

import hashlib
import random
from datetime import date

from flask import Flask, render_template, request


app = Flask(__name__)


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
]

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


def daily_fortune(name: str, birthday: str) -> dict[str, object]:
    seed_text = f"{date.today().isoformat()}:{name.strip()}:{birthday}"
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    fortune = dict(rng.choice(FORTUNES))
    fortune["lucky_number"] = rng.randint(1, 99)
    number = life_path_number(birthday)
    oni_type = LIFE_PATHS[number]
    fortune.update(life_path=number, **oni_type)
    fortune["premium_type"] = premium_oni_type(name, birthday)
    return fortune


@app.get("/")
def index():
    return render_template("index.html", today=date.today())


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/fortune")
def fortune():
    name = request.form.get("name", "").strip()[:30]
    birthday = request.form.get("birthday", "")
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
        ), 400
    return render_template(
        "result.html",
        today=date.today(),
        name=name,
        birthday=birthday,
        fortune=daily_fortune(name, birthday),
    )


@app.get("/premium")
def premium():
    return render_template(
        "premium.html",
        oni_count=len(LIFE_PATHS) * len(ONI_ASPECTS),
        aspects=ONI_ASPECTS,
    )


if __name__ == "__main__":
    app.run(debug=True)
