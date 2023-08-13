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

"""Route module."""

from http import HTTPStatus
from flask import Blueprint
from flasgger import swag_from
from pysui_flask.api.model.account import AccountModel
from pysui_flask.api.schema.account import AccountSchema

home_api = Blueprint("api", __name__)


@home_api.route("/")
@swag_from(
    {
        "responses": {
            HTTPStatus.OK.value: {
                "description": "Welcome to the pysui REST Api Server",
                "schema": AccountSchema,
            }
        }
    }
)
def welcome():
    """1 liner about the route.

    A more detailed description of the endpoint
    ---
    """
    result = AccountModel()
    return AccountSchema().dump(result), 200
