import importlib.util
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("yokai_app", Path(__file__).parents[1] / "yokai_fortune" / "app.py")
yokai_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(yokai_app)


def test_yokai_reading_has_signature_opening_and_seven_nights():
    reading = yokai_app.yokai_reading("健太", "1990-01-01")
    assert reading["scent"] in yokai_app.YOKAI_SCENTS
    assert reading["opening"].startswith(f"{reading['scent']}の匂いがする……お前の匂いだ。")
    assert len(reading["seven_nights"]) == 7
    assert all(item["creature"] in dict((name, detail) for name, detail, _ in yokai_app.YOKAI) for item in reading["seven_nights"])


def test_yokai_result_renders_seven_night_section():
    response = yokai_app.app.test_client().post("/", data={"name": "健太", "birthday": "1990-01-01", "state": "tired"})
    assert response.status_code == 200
    assert "の匂いがする……お前の匂いだ。" in response.text
    assert "七夜の気配" in response.text
    assert response.text.count("夜") >= 7
    assert "今の状態・疲れている" in response.text


def test_yokai_state_changes_reading_deterministically():
    tired = yokai_app.yokai_reading("健太", "1990-01-01", "tired")
    tired_again = yokai_app.yokai_reading("健太", "1990-01-01", "tired")
    clear = yokai_app.yokai_reading("健太", "1990-01-01", "clear")
    assert tired == tired_again
    assert tired["state_label"] == "疲れている"
    assert tired["state_message"] != clear["state_message"]


def test_yokai_analytics_accepts_only_anonymous_known_events():
    client = yokai_app.app.test_client()
    assert client.post("/events", json={"event": "page_view", "name": "秘密"}).status_code == 204
    assert client.post("/events", json={"event": "unknown"}).status_code == 400


def test_yokai_premium_preparation_page_is_available():
    response = yokai_app.app.test_client().get("/premium")
    assert response.status_code == 200
    assert "深層読み" in response.text
    assert "一銭も取らねえ" in response.text
