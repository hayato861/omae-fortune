from __future__ import annotations

import hashlib
from datetime import date

from flask import Flask, render_template, request


app = Flask(__name__)

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


def yokai_reading(name: str, birthday: str) -> dict[str, str]:
    digest = hashlib.sha256(f"yokai:{name.strip()}:{birthday}:{date.today().isoformat()}".encode()).digest()
    creature, title, advice = YOKAI[digest[0] % len(YOKAI)]
    omen = (digest[1] % 5) + 1
    return {"creature": creature, "title": title, "advice": advice, "omen": str(omen)}


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
