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

from flask import Flask
from flasgger import Swagger
from pysui_flask.api.route.home import home_api


def create_app():
    """."""
    app = Flask(__name__)

    app.config["SWAGGER"] = {
        "title": "pysui-flask REST Api",
    }
    swagger = Swagger(app)
    ## Initialize Config
    app.config.from_pyfile("config.py")
    app.register_blueprint(home_api)

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
