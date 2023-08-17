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
from datetime import datetime
from flask import Flask
from flask_session import Session
from flasgger import Swagger
from . import db
import pysui_flask.config as config

from pysui_flask.db_tables import *


from pysui_flask.api.route.account import account_api
from pysui_flask.api.route.admin import admin_api
from pysui.sui.sui_crypto import create_new_keypair


def _pre_populate(app):
    """Checks for at least the admin constructs."""
    result: User = User.query.filter_by(
        password=app.config["ADMIN_PASSWORD"]
    ).first()
    if not result:
        _, kp = create_new_keypair()
        user = User()
        user.user_key = kp.serialize()
        user.password = app.config["ADMIN_PASSWORD"]
        user.email = app.config["ADMIN_NAME"]
        user.user_role = UserRole.admin
        user.applicationdate = datetime.now()
        db.session.add(user)
        db.session.commit()
    elif result.user_role != UserRole.admin:
        raise SystemError("You've been hacked!")


def create_app():
    """Flask app entry point."""
    app = Flask(__name__)

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
        _pre_populate(app)
    # Blueprint routes
    app.register_blueprint(admin_api)
    app.register_blueprint(account_api)
    return app


if __name__ == "__main__":
    app = create_app()

    app.run(host="0.0.0.0", port=5000)
