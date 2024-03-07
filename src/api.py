"""
Code that interfaces with the Strava API. All requests to the API are wrapped
here to automatically handle new access token generation etc.
"""
import threading
import time

import flask
import requests as rq
from werkzeug.serving import make_server

import configure


AUTH_URL = "https://www.strava.com/oauth/authorize"
HOST = "127.0.0.1"
PORT = 9183


class ServerThread(threading.Thread):

    def __init__(self, app: flask.Flask) -> None:
        threading.Thread.__init__(self, target=self.run)
        self.server = make_server(HOST, PORT, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self) -> None:
        self.server.serve_forever()

    def shutdown(self) -> None:
        self.server.shutdown()


def request_access(config: configure.Config) -> None:
    """
    Performs one-time OAuth authentication to obtain recurring refresh token.
    """
    app = flask.Flask(__name__)
    code = None

    @app.route("/success")
    def success():
        print("Hi")
        global code
        code = 1
        return "Success."
    
    thread = ServerThread(app)
    thread.start()
    time.sleep(3)
    import webbrowser
    webbrowser.open(f"{AUTH_URL}?client_id={config.client_id}&redirect_uri=https://127.0.0.1:{PORT}&response_type=code&scope=read")

    while code is None:
        time.sleep(0.25)
        print("Hi")
    
    thread.shutdown()

import configure
request_access(configure.get_config())