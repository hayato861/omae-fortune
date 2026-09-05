from app import LIFE_PATHS, ONI_ASPECTS, app, daily_fortune, life_path_number, premium_oni_type
from analytics_report import parse_json_stream, summarize


def test_home_page():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "お前のためだけの占い" in response.text
    assert "hyakuretsuki-v2.webp" in response.text
    assert 'class="title-tail"' in response.text
    assert '<span class="no-break">百烈鬼</span>' in response.text
    assert 'href="#main-content"' in response.text
    assert 'data-fortune-form' in response.text
    assert response.text.count("data-date-part") == 3


def test_fortune_requires_fields():
    client = app.test_client()
    response = client.post("/fortune", data={})
    assert response.status_code == 400
    assert 'role="alert"' in response.text


def test_health_check_and_security_headers():
    client = app.test_client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_analytics_accepts_only_known_anonymous_events():
    client = app.test_client()
    assert client.post("/events", json={"event": "share_completed"}).status_code == 204
    assert client.post("/events", json={"event": "unknown"}).status_code == 400


def test_render_log_summary_ignores_health_checks():
    raw = """{"message":"127.0.0.1 - - [date] \\\"GET / HTTP/1.1\\\" 200 100"}
{"message":"127.0.0.1 - - [date] \\\"GET /healthz HTTP/1.1\\\" 200 16"}
{"message":"{\\\"event\\\": \\\"share_completed\\\"}"}"""
    assert summarize(parse_json_stream(raw)) == {"page_views": 1, "share_completed": 1}


def test_fortune_is_stable_for_same_inputs():
    assert daily_fortune("健太", "1990-01-01") == daily_fortune("健太", "1990-01-01")


def test_segmented_birthday_fields_submit_and_survive_errors():
    client = app.test_client()
    response = client.post("/fortune", data={"name": "健太", "birthday_year": "1990", "birthday_month": "1", "birthday_day": "1"})
    assert response.status_code == 200
    invalid = client.post("/fortune", data={"name": "健太", "birthday_year": "1990", "birthday_month": "13", "birthday_day": "40"})
    assert invalid.status_code == 400
    assert 'value="1990"' in invalid.text
    assert 'value="13"' in invalid.text


def test_life_path_number():
    assert life_path_number("1995-12-05") == 5
    assert life_path_number("1990-01-01") == 3


def test_every_oni_type_has_complete_profile():
    required = {"name", "role", "reading", "weapon", "weakness", "person", "hell", "escape", "match", "clash"}
    assert len(LIFE_PATHS) == 12
    assert all(required == set(profile) for profile in LIFE_PATHS.values())


def test_premium_has_sixty_oni_combinations():
    assert len(LIFE_PATHS) * len(ONI_ASPECTS) == 60
    result = premium_oni_type("健太", "1990-01-01")
    assert result["full_name"].endswith(tuple(aspect["name"] for aspect in ONI_ASPECTS))


def test_result_page():
    client = app.test_client()
    response = client.post("/fortune", data={"name": "健太", "birthday": "1990-01-01"})
    assert response.status_code == 200
    assert "健太の運勢" in response.text
    assert "極み版" in response.text
    assert "守護鬼" in response.text
    assert "気をつけるべき地獄" in response.text
    assert "data-share-weapon" in response.text
    assert "画像つきで鬼印を知らせる" in response.text
    assert 'class="has-mobile-cta"' in response.text


def test_premium_page_promises_sixty_oni():
    response = app.test_client().get("/premium")
    assert response.status_code == 200
    assert "全60鬼" in response.text
    assert "迷いを断ち、最短の一手を選ぶ" in response.text
