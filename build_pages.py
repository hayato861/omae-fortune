from __future__ import annotations

import json
import shutil
from pathlib import Path

from app import DAY_DETAILS, FORTUNES, LIFE_PATHS, ONI_ASPECTS, app


BACKEND_ORIGIN = "https://omae-fortune.onrender.com"
PAGES_ORIGIN = "https://hayato861.github.io/omae-fortune"
ROOT = Path(__file__).parent
OUTPUT = ROOT / "_site"


def build() -> Path:
    with app.test_client() as client:
        html = client.get("/").text

    replacements = {
        'action="/fortune"': f'action="{BACKEND_ORIGIN}/fortune"',
        'href="/premium"': f'href="{BACKEND_ORIGIN}/premium"',
        'href="/static/': 'href="static/',
        'src="/static/': 'src="static/',
        "http://localhost/static/": f"{PAGES_ORIGIN}/static/",
        'content="http://localhost/"': f'content="{PAGES_ORIGIN}/"',
        '<body class="">': f'<body class="" data-backend-origin="{BACKEND_ORIGIN}">',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)

    # JavaScript対応ブラウザでは無料鑑定をPages内で完結させる。JSが無効なら
    # 従来どおりRenderへのPOSTがフォールバックになる。
    html = html.replace('data-fortune-form>', 'data-fortune-form data-static-fortune>')
    html = html.replace('</body>', '<script src="static/static-fortune.js"></script></body>')

    shutil.rmtree(OUTPUT, ignore_errors=True)
    OUTPUT.mkdir()
    (OUTPUT / "index.html").write_text(html, encoding="utf-8")

    with app.test_client() as client:
        result_html = client.post("/fortune", data={"name": "小便小僧", "birthday": "1990-01-01"}).text
    result_html = result_html.replace('href="/static/', 'href="static/').replace('src="/static/', 'src="static/')
    result_html = result_html.replace('data-card-image="/static/', 'data-card-image="static/')
    result_html = result_html.replace('href="/premium"', f'href="{BACKEND_ORIGIN}/premium"')
    result_html = result_html.replace('href="/"', 'href="./"')
    result_html = result_html.replace('<body class="has-mobile-cta">', f'<body class="has-mobile-cta" data-backend-origin="{BACKEND_ORIGIN}" data-public-origin="{PAGES_ORIGIN}" data-static-result>')
    data = json.dumps({"fortunes": FORTUNES, "days": DAY_DETAILS, "oni": LIFE_PATHS, "aspects": ONI_ASPECTS}, ensure_ascii=False, separators=(",", ":"))
    result_html = result_html.replace('</body>', f'<script>window.FORTUNE_DATA={data};</script><script src="static/static-fortune.js"></script></body>')
    (OUTPUT / "result.html").write_text(result_html, encoding="utf-8")
    (OUTPUT / ".nojekyll").touch()
    shutil.copytree(ROOT / "static", OUTPUT / "static")
    return OUTPUT


if __name__ == "__main__":
    print(build())
