import requests

from llm_rewrite import rewrite_why


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._json_data


def test_rewrite_why_returns_original_without_api_key():
    result = rewrite_why("Recommended by 3 favorites.", "Tenet", "profile", api_key="")
    assert result == "Recommended by 3 favorites."


def test_rewrite_why_returns_rewritten_text_on_success(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse(
            200,
            {"choices": [{"message": {"content": "A slick, mind-bending Nolan thriller you'll love."}}]},
        )

    monkeypatch.setattr(requests, "post", fake_post)
    result = rewrite_why("Recommended by 3 favorites.", "Tenet", "profile", api_key="fake-key")
    assert result == "A slick, mind-bending Nolan thriller you'll love."


def test_rewrite_why_falls_back_on_http_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse(500, {})

    monkeypatch.setattr(requests, "post", fake_post)
    original = "Recommended by 3 favorites."
    result = rewrite_why(original, "Tenet", "profile", api_key="fake-key")
    assert result == original


def test_rewrite_why_falls_back_on_network_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(requests, "post", fake_post)
    original = "Recommended by 3 favorites."
    result = rewrite_why(original, "Tenet", "profile", api_key="fake-key")
    assert result == original


def test_rewrite_why_falls_back_on_malformed_response(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse(200, {"unexpected": "shape"})

    monkeypatch.setattr(requests, "post", fake_post)
    original = "Recommended by 3 favorites."
    result = rewrite_why(original, "Tenet", "profile", api_key="fake-key")
    assert result == original
