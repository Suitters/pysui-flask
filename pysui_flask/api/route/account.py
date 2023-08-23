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
import json

# from http import HTTPStatus
from flask import Blueprint, session, request

from pysui_flask.api.schema.account import OutUser

# from flasgger import swag_from
from . import UserRole, verify_credentials, CustomJSONEncoder
from pysui_flask.db_tables import User
from pysui_flask.api_error import ErrorCodes, APIError

account_api = Blueprint("account", __name__, url_prefix="/account")


def _user_login_required():
    if not session.get("user_logged_in"):
        raise APIError("User must login first", ErrorCodes.LOGIN_REQUIRED)


@account_api.get("/")
# @swag_from(
#     {
#         "responses": {
#             HTTPStatus.OK.value: {
#                 "description": "Admin for pysui-flask",
#             }
#         }
#     }
# )
def account():
    """Account root."""
    _user_login_required()
    user = User.query.filter(User.account_key == session["user_key"]).first()
    ujson = json.loads(json.dumps(user, cls=CustomJSONEncoder))
    ujson["configuration"] = json.loads(
        json.dumps(user.configuration, cls=CustomJSONEncoder)
    )
    return {
        "account": OutUser(partial=True, unknown="exclude", many=False).load(
            ujson
        )
    }, 200


@account_api.get("/login")
def account_login():
    """Verify account login."""
    if not session.get("user_logged_in"):
        in_data = json.loads(request.get_json())
        user: User = verify_credentials(
            username=in_data["username"],
            user_password=in_data["password"],
            expected_role=UserRole.user,
        )
        session["name"] = in_data["username"]
        session["user_key"] = user.account_key
        session["user_logged_in"] = True
    return {"session": session.sid}
