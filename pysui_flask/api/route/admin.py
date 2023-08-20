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
from datetime import datetime
from http import HTTPStatus
from flask import (
    Blueprint,
    session,
    request,
)
from flasgger import swag_from
import marshmallow
from sqlalchemy import and_

from pysui_flask import db
from . import UserRole, verify_credentials, str_to_hash_hex, User
from pysui_flask.db_tables import UserConfiguration
from pysui_flask.api_error import *
from pysui_flask.api.schema.account import (
    InAccountSetup,
    deserialize_account_setup,
)

from pysui import SuiAddress
from pysui.sui.sui_crypto import create_new_keypair, keypair_from_keystring


admin_api = Blueprint("admin", __name__)


def _admin_login_required():
    if not session.get("admin_logged_in"):
        raise APIError("Admin must login first", ErrorCodes.LOGIN_REQUIRED)


def _content_expected(fields):
    raise APIError(
        f"Expected {fields} in request", ErrorCodes.REQUEST_CONTENT_ERROR
    )


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
            username=in_data["username"],
            user_password=in_data["password"],
            expected_role=UserRole.admin,
        )
        session["name"] = in_data["username"]
        session["admin_logged_in"] = True
    return {"session": session.sid}


# Add user account - required admin logged in


def _new_user_reg(user_config: InAccountSetup) -> User:
    """."""
    # Create the user
    user = User()
    # Create a new identifying key
    _, kp = create_new_keypair()
    user.account_key = kp.serialize()
    # Hash the user password
    user.password = str_to_hash_hex(user_config.user.password)
    user.user_name_or_email = user_config.user.username
    user.user_role = UserRole.user
    user.applicationdate = datetime.now()

    # Create the configuration
    cfg = UserConfiguration()
    cfg.rpc_url = user_config.config.urls.rpc_url
    cfg.ws_url = user_config.config.urls.ws_url
    cfg.private_key = user_config.config.private_key
    # Get the keypair from private seed
    kp = keypair_from_keystring(user_config.config.private_key)
    # Convert to address
    cfg.active_address = SuiAddress.from_bytes(
        kp.public_key.scheme_and_key()
    ).address

    # Create the relationship
    user.configuration = cfg
    # Add and commit
    db.session.add(user)
    db.session.commit()

    return user


@admin_api.post("/user_account")
def new_user_account():
    """Admin registration of new user account."""
    _admin_login_required()
    try:
        # Deserialize
        user_in: InAccountSetup = deserialize_account_setup(
            json.loads(request.get_json())
        )
        # Check if user exists
        user = User.query.filter(
            and_(
                User.user_name_or_email.like(user_in.user.username),
                User.user_role == UserRole.user,
            )
        ).first()
    except marshmallow.ValidationError as ve:
        _content_expected(ve.messages)
    # When we have a user with username and User role, fail
    if user:
        raise APIError(
            f"Username {user_in.user.username} already exists.",
            ErrorCodes.USER_ALREADY_EXISTS,
        )
    # Create the new user and configuration
    user_persist = _new_user_reg(user_in)
    return {
        "created": {
            "user_name": user_in.user.username,
            "account_key": user_persist.account_key,
        }
    }, 201


@admin_api.get("/user_account")
def query_user_account():
    """."""
    _admin_login_required()
    q_account = json.loads(request.get_json())

    user = User.query.filter(
        User.account_key == q_account["account_key"],
    ).first()
    if user:
        return {
            "account": {
                "user_name": user.user_name_or_email,
                "user_role": user.user_role.value,
            }
        }, 200
