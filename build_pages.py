from __future__ import annotations

import shutil
from pathlib import Path

from app import app


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

    shutil.rmtree(OUTPUT, ignore_errors=True)
    OUTPUT.mkdir()
    (OUTPUT / "index.html").write_text(html, encoding="utf-8")
    (OUTPUT / ".nojekyll").touch()
    shutil.copytree(ROOT / "static", OUTPUT / "static")
    return OUTPUT


if __name__ == "__main__":
    print(build())
