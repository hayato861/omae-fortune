from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from flask import Flask, render_template, request


ROOT = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))

YOKAI = [
    ("河童", "流れを読むもの", "急がず、今日ひとつだけ水面を変えよ。"),
    ("天狗", "高みから見渡すもの", "正しさを振りかざす前に、足元の声を聞け。"),
    ("鎌鼬", "風の隙間を走るもの", "迷いの間に、短い一手を差し込め。"),
    ("雪女", "静けさを抱くもの", "冷えた心を無理に溶かすな。距離にも意味がある。"),
    ("ぬらりひょん", "境界をすり抜けるもの", "他人の期待を、てめえの役目と取り違えるな。"),
    ("座敷童子", "暮らしに福を置くもの", "小さな習慣を整えれば、運の居場所ができる。"),
    ("ぬりかべ", "道を塞ぎ守るもの", "進めない日は、守られている場所を見つけよ。"),
    ("猫又", "過去を覚えているもの", "昔の傷を、今日の相手に重ねて見るな。"),
    ("一反木綿", "夜空を渡るもの", "一人で抱えず、誰かの風を借りて飛べ。"),
    ("鬼火", "暗がりを照らすもの", "小さな違和感を無視するな。そこに道がある。"),
    ("狐", "姿を変えるもの", "好かれる顔を増やすほど、本当の声を失う。"),
    ("目目連", "見えないものを見るもの", "答えを探す前に、見落としている事実を書き出せ。"),
]
YOKAI_IMAGES = {
    "河童": "yokai-kappa.png", "天狗": "yokai-tengu.png", "鎌鼬": "yokai-kamaitachi.png", "雪女": "yokai-yukionna.png",
    "ぬらりひょん": "yokai-nurarihyon.png", "座敷童子": "yokai-zashikiwarashi.png", "ぬりかべ": "yokai-nurikabe.png", "猫又": "yokai-nekomata.png",
    "一反木綿": "yokai-ittanmomen.png", "鬼火": "yokai-onibi.png", "狐": "yokai-kitsune.png", "目目連": "yokai-mokumokuren.png",
}
YOKAI_DETAILS = {
    "河童": ("流れが変わる前兆", "人との約束やお金の流れを整える夜", "返事と支払いを一つだけ片づける", "勢いだけで新しい約束を増やす"),
    "天狗": ("高い視点と孤独", "正しさが先に立ち、周りの声が遠くなる夜", "反対意見を一人だけ聞く", "勝ち負けで人を測る"),
    "鎌鼬": ("速さと切れ味", "短い決断が停滞を切り裂く夜", "五分で終わる一手から始める", "急いで大事な返事を送る"),
    "雪女": ("静けさと距離", "無理に近づかず、心を冷ます時間が必要な夜", "通知を切って一人の時間を持つ", "寂しさだけで連絡する"),
    "ぬらりひょん": ("境界を越える知恵", "他人の役目を背負わされやすい夜", "自分の担当を一文で決める", "頼まれていない世話まで焼く"),
    "座敷童子": ("小さな福と習慣", "暮らしを整えた場所に運が居つく夜", "机か財布を一か所だけ整える", "大きな幸運を待って動かない"),
    "ぬりかべ": ("守りと境界線", "進めないことが、今は守りになる夜", "やらないことを一つ決める", "壁を理由に全てを諦める"),
    "猫又": ("記憶と執着", "昔の出来事が今の判断に混ざる夜", "過去と今を紙に分けて書く", "昔の相手を今の人に重ねる"),
    "一反木綿": ("風と身軽さ", "一人で抱えるほど、動きが鈍くなる夜", "誰かに一つだけ頼る", "全部を自力で片づける"),
    "鬼火": ("違和感と導き", "小さな引っかかりが道を照らす夜", "気になったことを一行だけ記録する", "不安を無視して突き進む"),
    "狐": ("変化と本音", "場に合わせる顔が増えすぎる夜", "本当の希望を一つ口にする", "好かれるために約束を増やす"),
    "目目連": ("観察と見落とし", "見えていない事実が答えを隠す夜", "事実と想像を別々に書く", "推測だけで誰かを裁く"),
}


def yokai_reading(name: str, birthday: str) -> dict[str, str]:
    digest = hashlib.sha256(f"yokai:{name.strip()}:{birthday}:{date.today().isoformat()}".encode()).digest()
    creature, title, advice = YOKAI[digest[0] % len(YOKAI)]
    omen = (digest[1] % 5) + 1
    nature, sign, move, avoid = YOKAI_DETAILS[creature]
    return {"creature": creature, "title": title, "advice": advice, "omen": str(omen), "image": YOKAI_IMAGES[creature], "nature": nature, "sign": sign, "move": move, "avoid": avoid}


@app.route("/", methods=["GET", "POST"])
def index():
    name = request.form.get("name", "").strip()
    birthday = request.form.get("birthday", "")
    if request.method == "POST" and not birthday:
        birthday = "-".join([
            request.form.get("birthday_year", ""),
            request.form.get("birthday_month", ""),
            request.form.get("birthday_day", ""),
        ])
    reading = None
    error = None
    if request.method == "POST":
        try:
            born = date.fromisoformat(birthday)
            if not name or born > date.today():
                raise ValueError
        except ValueError:
            error = "名前と生年月日を、静かに置いていけ。"
        else:
            reading = yokai_reading(name, birthday)
            return render_template("result.html", name=name, reading=reading)
    birthday_parts = birthday.split("-") if birthday.count("-") == 2 else ["", "", ""]
    return render_template("index.html", name=name, birthday=birthday, birthday_year=birthday_parts[0], birthday_month=birthday_parts[1], birthday_day=birthday_parts[2], reading=reading, error=error)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
