"""
Code that interfaces with the Strava API. All requests to the API are wrapped
here to automatically handle new access token generation etc.
"""
import json
import socket
import threading
import time
import webbrowser
from contextlib import closing
from typing import Callable

import flask
import requests as rq
from werkzeug.serving import make_server

import configure
from const import CREDENTIALS_FILE


AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
DEFAULT_MAX_REQUEST_ATTEMPTS = 3
RENEW_SECONDS_BEFORE_EXPIRY = 600


def post(
    url: str, data: dict, validate_function: Callable = None,
    attempts: int = DEFAULT_MAX_REQUEST_ATTEMPTS
) -> rq.Response:
    """
    POST request wrapper for retrying. Specify a validation
    function to check status code etc. before returning response.
    """
    while True:
        try:
            response = rq.post(url, data)
            if (
                validate_function is not None
                and not validate_function(response)
            ):
                raise RuntimeError("Validation failed.")
            return response
        except Exception as e:
            attempts -= 1
            if not attempts:
                raise e


def get_free_port() -> int:
    """Returns a free port on device to perform OAuth authentication."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
    

HOST = "127.0.0.1"
PORT = get_free_port()


class ServerThread(threading.Thread):
    """Flask server thread - run while the program waits for auth code."""

    def __init__(self, app: flask.Flask) -> None:
        threading.Thread.__init__(self, target=self.run, daemon=True)
        self.server = make_server(HOST, PORT, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self) -> None:
        """Starts the flask server."""
        self.server.serve_forever()

    def shutdown(self) -> None:
        """Stops the flask server."""
        self.server.shutdown()


def get_code(config: configure.Config) -> str:
    """
    Returns the one-time OAuth code for authentication.
    Uses a local Flask server to achieve this.
    """
    app = flask.Flask(__name__)
    app.strava_oauth_code = None

    @app.route("/")
    def _():
        app.strava_oauth_code = flask.request.args.get("code") or ""
        if not app.strava_oauth_code:
            return "<h1>Strava Automation - Cancelled.</h1>"
        return "<h1>Strava Automation - Successful OAuth Authentication.</h1>"
    
    thread = ServerThread(app)
    thread.start()
    time.sleep(3)
    params = {
        "client_id": config.client_id,
        "redirect_uri": f"http://127.0.0.1:{PORT}",
        "response_type": "code",
        "scope": "activity:read_all,activity:write"
    }
    webbrowser.open(
        f"{AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}")
    while app.strava_oauth_code is None:
        time.sleep(0.25)    
    thread.shutdown()
    code = app.strava_oauth_code
    if not code:
        raise RuntimeError("OAuth Authentication cancelled.")
    return code


def get_token_info(config: configure.Config, code: str) -> dict:
    """Returns the token JSON response from exhancing for a token."""
    params = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "code": code,
        "grant_type": "authorization_code"
    }
    return post(
        TOKEN_URL, params, lambda response: response.status_code == 200).json()


def request_access(config: configure.Config) -> None:
    """
    Performs one-time OAuth authentication to obtain recurring refresh token.
    """
    code = get_code(config)
    token_info = get_token_info(config, code)
    data = {
        "access": token_info["access_token"],
        "refresh": token_info["refresh_token"],
        "expiry": token_info["expires_at"]
    }
    with CREDENTIALS_FILE.open("w", encoding="utf8") as f:
        json.dump(data, f)


def renew_access(config: configure.Config, refresh_token: str) -> None:
    """Renews access to the API by getting a new access token."""
    # TODO


def get_access_token(config: configure.Config) -> str:
    """
    Returns the access token, either requesting access or
    checking for expiration and refreshing if needed.
    """
    if not CREDENTIALS_FILE.is_file():
        request_access(config)
    try:
        with CREDENTIALS_FILE.open("r", encoding="utf8") as f:
            data = json.load(f)
        timestamp = time.time()
        if timestamp >= data["expiry"] - RENEW_SECONDS_BEFORE_EXPIRY:
            renew_access(config, data["refresh"])
            return get_access_token(config)
        # Successfully found access token, not even close to expiry.
        return data["access"]
    except Exception:
        # Recursive retry with invalid credentials file removed.
        # Recursion fine because limit will not practically be reached.
        CREDENTIALS_FILE.unlink(missing_ok=True)
        return get_access_token(config)
