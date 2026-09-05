from app import LIFE_PATHS, ONI_ASPECTS, app, daily_fortune, life_path_number, premium_oni_type


def test_home_page():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "お前のためだけの占い" in response.text
    assert "hyakuretsuki-v2.webp" in response.text
    assert 'href="#main-content"' in response.text
    assert 'data-fortune-form' in response.text


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


def test_fortune_is_stable_for_same_inputs():
    assert daily_fortune("健太", "1990-01-01") == daily_fortune("健太", "1990-01-01")


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
    assert 'class="has-mobile-cta"' in response.text


def test_premium_page_promises_sixty_oni():
    response = app.test_client().get("/premium")
    assert response.status_code == 200
    assert "全60鬼" in response.text
    assert "迷いを断ち、最短の一手を選ぶ" in response.text
