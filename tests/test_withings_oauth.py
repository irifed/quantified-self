from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from scripts.withings_oauth import OAuthSettings, build_authorization_url, create_app, save_tokens


def settings(env_path: Path) -> OAuthSettings:
    return OAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8123/oauth/callback",
        env_path=env_path,
    )


def test_authorization_url_contains_required_parameters(tmp_path: Path) -> None:
    url = build_authorization_url(settings(tmp_path / ".env"), "expected-state")
    query = parse_qs(urlsplit(url).query)

    assert query == {
        "response_type": ["code"],
        "client_id": ["client-id"],
        "scope": ["user.metrics"],
        "redirect_uri": ["http://localhost:8123/oauth/callback"],
        "state": ["expected-state"],
    }


def test_public_redirect_does_not_change_local_bind_address(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "WITHINGS_CLIENT_ID=client-id\n"
        "WITHINGS_CLIENT_SECRET=client-secret\n"
        "WITHINGS_REDIRECT_URI=https://example.ngrok-free.dev/callback\n"
    )

    result = OAuthSettings.from_env(env_path)

    assert result.redirect_uri == "https://example.ngrok-free.dev/callback"
    assert result.callback_path == "/callback"
    assert result.host == "127.0.0.1"
    assert result.port == 8000


def test_callback_exchanges_and_saves_tokens(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("WITHINGS_CLIENT_ID=client-id\nUNCHANGED=value\n")
    app = create_app(
        settings(env_path),
        state="expected-state",
        token_exchange=lambda _settings, code: {
            "access_token": f"access-{code}",
            "refresh_token": "refresh-token",
        },
        open_browser=False,
    )

    with TestClient(app) as client:
        response = client.get("/oauth/callback?code=auth-code&state=expected-state")

    assert response.status_code == 200
    contents = env_path.read_text()
    assert "UNCHANGED=value" in contents
    assert "WITHINGS_ACCESS_TOKEN=access-auth-code" in contents
    assert "WITHINGS_REFRESH_TOKEN=refresh-token" in contents
    output = capsys.readouterr().out
    assert "WITHINGS_ACCESS_TOKEN=access-auth-code" in output
    assert "WITHINGS_REFRESH_TOKEN=refresh-token" in output


def test_callback_rejects_invalid_state(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / ".env"), state="expected", open_browser=False)

    with TestClient(app) as client:
        response = client.get("/oauth/callback?code=auth-code&state=wrong")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OAuth state"


def test_root_redirect_uri_processes_callback_instead_of_reauthorizing(tmp_path: Path) -> None:
    oauth_settings = OAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="https://example.ngrok-free.dev",
        env_path=tmp_path / ".env",
    )
    completed: list[bool] = []
    app = create_app(
        oauth_settings,
        state="expected",
        token_exchange=lambda _settings, _code: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
        },
        open_browser=False,
        on_success=lambda: completed.append(True),
    )

    with TestClient(app) as client:
        response = client.get("/?code=auth-code&state=expected")

    assert response.status_code == 200
    assert "authorization complete" in response.text
    assert completed == [True]


def test_save_tokens_replaces_existing_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("WITHINGS_ACCESS_TOKEN=old\nWITHINGS_REFRESH_TOKEN=old\n")

    save_tokens(env_path, "new-access", "new-refresh")

    assert env_path.read_text().splitlines() == [
        "WITHINGS_ACCESS_TOKEN=new-access",
        "WITHINGS_REFRESH_TOKEN=new-refresh",
    ]
