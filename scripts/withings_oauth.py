#!/usr/bin/env python3
"""Run a local Withings OAuth 2.0 authorization-code flow."""

import secrets
import webbrowser
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
import uvicorn
from dotenv import dotenv_values, set_key
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

AUTHORIZATION_URL = "https://account.withings.com/oauth2_user/authorize2"
TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
DEFAULT_SCOPE = "user.metrics"


@dataclass(frozen=True)
class OAuthSettings:
    client_id: str
    client_secret: str
    redirect_uri: str
    env_path: Path
    scope: str = DEFAULT_SCOPE
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls, env_path: Path = Path(".env")) -> "OAuthSettings":
        values = dotenv_values(env_path)
        required = {
            "WITHINGS_CLIENT_ID": values.get("WITHINGS_CLIENT_ID"),
            "WITHINGS_CLIENT_SECRET": values.get("WITHINGS_CLIENT_SECRET"),
            "WITHINGS_REDIRECT_URI": values.get("WITHINGS_REDIRECT_URI"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required settings in {env_path}: {', '.join(missing)}")
        return cls(
            client_id=str(required["WITHINGS_CLIENT_ID"]),
            client_secret=str(required["WITHINGS_CLIENT_SECRET"]),
            redirect_uri=str(required["WITHINGS_REDIRECT_URI"]),
            env_path=env_path,
            host=str(values.get("WITHINGS_OAUTH_HOST") or "127.0.0.1"),
            port=int(values.get("WITHINGS_OAUTH_PORT") or 8000),
        )

    @property
    def callback_path(self) -> str:
        path = urlsplit(self.redirect_uri).path
        return path or "/"

def build_authorization_url(settings: OAuthSettings, state: str) -> str:
    parsed = urlsplit(AUTHORIZATION_URL)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.client_id,
            "scope": settings.scope,
            "redirect_uri": settings.redirect_uri,
            "state": state,
        }
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))


def exchange_code(settings: OAuthSettings, code: str) -> dict[str, Any]:
    response = httpx.post(
        TOKEN_URL,
        data={
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "redirect_uri": settings.redirect_uri,
            "code": code,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    if int(payload.get("status", -1)) != 0:
        raise RuntimeError(f"Withings token exchange failed with status {payload.get('status')}")
    body = payload.get("body")
    if not isinstance(body, dict) or not body.get("access_token") or not body.get("refresh_token"):
        raise RuntimeError("Withings token response did not contain access and refresh tokens")
    return body


def save_tokens(env_path: Path, access_token: str, refresh_token: str) -> None:
    env_path.touch(mode=0o600, exist_ok=True)
    set_key(str(env_path), "WITHINGS_ACCESS_TOKEN", access_token, quote_mode="never")
    set_key(str(env_path), "WITHINGS_REFRESH_TOKEN", refresh_token, quote_mode="never")


def create_app(
    settings: OAuthSettings,
    *,
    state: str | None = None,
    token_exchange: Callable[[OAuthSettings, str], dict[str, Any]] = exchange_code,
    open_browser: bool = True,
    on_success: Callable[[], None] | None = None,
) -> FastAPI:
    expected_state = state or secrets.token_urlsafe(32)
    authorization_url = build_authorization_url(settings, expected_state)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        print(f"Open this URL to authorize Withings:\n{authorization_url}")
        if open_browser:
            webbrowser.open(authorization_url)
        yield

    app = FastAPI(title="Withings OAuth Helper", lifespan=lifespan)

    def callback(
        background_tasks: BackgroundTasks,
        code: str | None = Query(default=None),
        state: str | None = Query(default=None),
        error: str | None = Query(default=None),
    ) -> HTMLResponse:
        if error:
            raise HTTPException(status_code=400, detail=f"Withings authorization failed: {error}")
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        if not secrets.compare_digest(state or "", expected_state):
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        try:
            tokens = token_exchange(settings, code)
            access_token = str(tokens["access_token"])
            refresh_token = str(tokens["refresh_token"])
            save_tokens(settings.env_path, access_token, refresh_token)
        except (httpx.HTTPError, RuntimeError, OSError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        print(f"WITHINGS_ACCESS_TOKEN={access_token}")
        print(f"WITHINGS_REFRESH_TOKEN={refresh_token}")
        print(f"Tokens saved to {settings.env_path}")
        if on_success is not None:
            background_tasks.add_task(on_success)
        return HTMLResponse(
            "<h1>Withings authorization complete</h1>"
            "<p>Access and refresh tokens were printed and saved to <code>.env</code>. "
            "You can close this window.</p>"
        )

    app.add_api_route(settings.callback_path, callback, methods=["GET"], include_in_schema=False)

    if settings.callback_path != "/":

        @app.get("/", include_in_schema=False)
        def authorize() -> RedirectResponse:
            return RedirectResponse(authorization_url)

    return app


def main() -> None:
    settings = OAuthSettings.from_env()
    server_holder: dict[str, uvicorn.Server] = {}

    def stop_server() -> None:
        server_holder["server"].should_exit = True

    app = create_app(settings, on_success=stop_server)
    config = uvicorn.Config(app, host=settings.host, port=settings.port)
    server = uvicorn.Server(config)
    server_holder["server"] = server
    server.run()


if __name__ == "__main__":
    main()
