"""Regression: /api/observations/voice-checkin must not 500 when Ollama is
down, for ANY transcript — the heuristic fallback must only use valid
VoiceDisruptionIntent literals (was: 'general_delay' -> 500 for every
transcript without 'late'/'woke', i.e. most Hindi/Marathi/Hinglish input).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _checkin(client, text):
    return client.post(
        "/api/observations/voice-checkin",
        json={"transcript": text, "source_device": "mobile_mic"},
    )


def test_voice_checkin_non_late_disruption_no_500(client):
    r = _checkin(client, "Bixy: mala ushir zhala ahe")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert body["disruption_detected"] is True


def test_voice_checkin_clean_transcript_no_500(client):
    r = _checkin(client, "Bixy: feeling good, everything on track")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert body["disruption_detected"] is False
