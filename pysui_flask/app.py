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

import json

from flask import Flask, jsonify, request
from flask_session import Session
from flasgger import Swagger

from pysui_flask.api_error import ErrorCodes, APIError
from . import db
import pysui_flask.config as config

# Routes
from .api.admin_route import admin_api
from .api.account_route import account_api
from .api.data_route import data_api


# user.password = app.config["ADMIN_PASSWORD"]
# user.user_name_or_email = app.config["ADMIN_NAME"]


app = Flask(__name__)


@app.errorhandler(APIError)
def invalid_api_usage(e):
    """Handle API raised exceptions."""
    return jsonify(e.to_dict())


@app.before_request
def pre_check():
    """Check it is json payloads."""
    if not (request.headers.get("Content-Type") == "application/json"):
        raise APIError(
            "Expect Content-Type=application/json",
            ErrorCodes.CONTENT_TYPE_ERROR,
        )

    return None


@app.after_request
def post_check(response):
    """Request message imbue with 'result' high level key."""
    if not response.get_json().get("error", None):
        response.data = json.dumps({"result": response.get_json()})
    return response


def create_app():
    """Flask app creation entry point."""
    # Swagger
    app.config["SWAGGER"] = {
        "title": "pysui-flask REST Api",
    }
    swagger = Swagger(app)

    # Configuration environmental variables
    app.config.from_object(config.load_config())

    # Session
    Session(app)
    # Db load
    db.init_app(app)
    with app.app_context() as actx:
        db.create_all()
    # Blueprint routes
    app.register_blueprint(admin_api)
    app.register_blueprint(account_api)
    app.register_blueprint(data_api)
    return app


if __name__ == "__main__":
    app = create_app()

    app.run(host="0.0.0.0", port=5000)
