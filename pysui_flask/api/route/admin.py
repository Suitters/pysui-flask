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

"""Administration module."""

import json
import functools
from http import HTTPStatus
from flask import (
    Blueprint,
    session,
    request,
)
from flasgger import swag_from
import marshmallow
from pysui_flask.api.schema.account import AccountSetup


from pysui_flask.api_error import (
    LOGIN_REQUIRED,
    REQUEST_CONTENT_ERROR,
    APIError,
)
from . import UserRole, verify_credentials


admin_api = Blueprint("admin", __name__)


def _admin_login_required():
    if not session.get("admin_logged_in"):
        raise APIError("Admin must login first", LOGIN_REQUIRED)


def _content_expected(fields):
    raise APIError(f"Expected {fields} in request", REQUEST_CONTENT_ERROR)


@admin_api.get("/")
@swag_from(
    {
        "responses": {
            HTTPStatus.OK.value: {
                "description": "Admin for pysui-flask",
            }
        }
    }
)
def admin():
    """Admin root.

    A more detailed description of the endpoint
    """
    _admin_login_required()
    return {"session": session.sid}


@admin_api.get("/login")
def admin_login():
    """Admin login with credential check."""
    if not session.get("admin_logged_in"):
        in_data = json.loads(request.get_json())
        # Get the User object of the admin role
        # Throws exception
        user = verify_credentials(
            user_name=in_data["username"],
            user_password=in_data["password"],
            expected_role=UserRole.admin,
        )
        session["name"] = in_data["username"]
        session["admin_logged_in"] = True
    return {"session": session.sid}


# Add user account - required admin logged in


@admin_api.post("/user_account")
def new_user_account():
    """Admin registration of new user account."""
    _admin_login_required()
    try:
        AccountSetup().load(json.loads(request.get_json()))
    except marshmallow.ValidationError as ve:
        _content_expected(ve.messages)
    # except UnsupportedMediaType as um:
    #     pass

    return {"User": "not added"}
