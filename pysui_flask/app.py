#    Copyright Frank V. Castellucci
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#        http://www.apache.org/licenses/LICENSE-2.0
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# -*- coding: utf-8 -*-

"""Application bootstrap."""

import os
from datetime import timedelta
from flask import Flask
from flask_session import Session
from flasgger import Swagger
from pysui_flask.api.route.account import account_api
from pysui_flask.api.route.admin import admin_api


def create_app():
    """."""
    app = Flask(__name__, template_folder="api/templates")

    app.config["SWAGGER"] = {
        "title": "pysui-flask REST Api",
    }
    swagger = Swagger(app)
    ## Initialize Config
    app.config.from_pyfile("config.py")
    if os.getenv("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
        app.config["SESSION_COOKIE_SECURE"] = True
    if os.getenv("USE_FLASK_SESSION") == "True":
        app.config["SESSION_TYPE"] = os.getenv("SESSION_TYPE")
        # if
        app.config["SESSION_PERMANENT"] = (
            True if os.getenv("SESSION_PERMANENT", None) else False
        )
        app.config["SESSION_FILE_THRESHOLD"] = int(
            os.getenv("SESSION_FILE_THRESHOLD", "10")
        )

        app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
            hours=(int(os.getenv("PERMANENT_SESSION_LIFETIME", "1")))
        )
        Session(app)

    app.register_blueprint(admin_api)
    app.register_blueprint(account_api)

    return app


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "-p", "--port", default=5000, type=int, help="port to listen on"
    )
    args = parser.parse_args()
    port = args.port

    app = create_app()

    app.run(host="0.0.0.0", port=port)
