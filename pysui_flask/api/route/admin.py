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


from functools import partial
import json

# from http import HTTPStatus
from operator import is_not
from flask import Blueprint, session, request

# from flasgger import swag_from
import marshmallow
from sqlalchemy import and_

from pysui_flask import db
from . import (
    CustomJSONEncoder,
    UserRole,
    verify_credentials,
    str_to_hash_hex,
    User,
)
from pysui_flask.db_tables import UserConfiguration
from pysui_flask.api_error import *
from pysui_flask.api.schema.account import (
    InAccountSetup,
    OutUser,
    deserialize_account_setup,
)

from pysui import SuiAddress
from pysui.sui.sui_crypto import create_new_keypair, keypair_from_keystring


admin_api = Blueprint("admin", __name__, url_prefix="/admin")


def _admin_login_required():
    if not session.get("admin_logged_in"):
        raise APIError("Admin must login first", ErrorCodes.LOGIN_REQUIRED)


def _content_expected(fields):
    raise APIError(
        f"Expected {fields} in request", ErrorCodes.REQUEST_CONTENT_ERROR
    )


@admin_api.get("/")
# @swag_from(
#     {
#         "responses": {
#             HTTPStatus.OK.value: {
#                 "description": "Admin for pysui-flask",
#             }
#         }
#     }
# )
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


def _new_user_reg(user_configs: list[InAccountSetup]) -> list[User]:
    """_summary_ Process one or more new user registrations.

    :param user_configs: list of one or more new account registrations
    :type user_configs: list[InAccountSetup]
    :return: List of committed User types
    :rtype: list[User]
    """
    users: list[User] = []
    for user_config in user_configs:
        # Create the user
        user = User()
        # Create a new identifying key
        _, kp = create_new_keypair()
        user.account_key = kp.serialize()
        # Hash the user password
        user.password = str_to_hash_hex(user_config.user.password)
        user.user_name_or_email = user_config.user.username
        user.user_role = UserRole.user

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
        users.append(user)
    db.session.commit()

    return users


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
    user_persist = _new_user_reg([user_in])
    return {
        "created": {
            "user_name": user_persist[0].user_name_or_email,
            "account_key": user_persist[0].account_key,
        }
    }, 201


@admin_api.post("/user_accounts")
def new_user_accounts():
    """Admin registration of bulk new user account."""
    _admin_login_required()
    try:
        # Deserialize
        users_in: InAccountSetup = deserialize_account_setup(
            json.loads(request.get_json())
        )
        # Check if user exists
        users = [
            User.query.filter(
                and_(
                    User.user_name_or_email.like(x.user.username),
                    User.user_role == UserRole.user,
                )
            ).first()
            for x in users_in
        ]
        users = list(filter(partial(is_not, None), users))
    except marshmallow.ValidationError as ve:
        _content_expected(ve.messages)
    # When we have a user with username and User role, fail
    if users:
        names = [x.user_name_or_email for x in users]
        raise APIError(
            f"Username {names} already exists.",
            ErrorCodes.USER_ALREADY_EXISTS,
        )
    # Create the new user and configuration
    user_result: list = []

    for users_persist in _new_user_reg(users_in):
        user_result.append(
            {
                "user_name": users_persist.user_name_or_email,
                "account_key": users_persist.account_key,
            }
        )
    return {"created": user_result}, 201


@admin_api.get("/user_account/key")
def query_user_account():
    """Get a user account by account key."""
    _admin_login_required()
    q_account = json.loads(request.get_json())

    user = User.query.filter(
        User.account_key == q_account["account_key"],
    ).first()
    if user:
        ujson = json.loads(json.dumps(user, cls=CustomJSONEncoder))
        ujson["configuration"] = json.loads(
            json.dumps(user.configuration, cls=CustomJSONEncoder)
        )
        return {
            "account": OutUser(
                partial=True, unknown="exclude", many=False
            ).load(ujson)
        }, 200
    raise APIError(
        f"Account {q_account} not exist.",
        ErrorCodes.ACCOUNT_NOT_FOUND,
    )


@admin_api.get("/user_accounts", defaults={"page": 1})
@admin_api.get("/user_accounts/<int:page>")
def query_user_accounts(page):
    """Fetches all user accounts."""
    _admin_login_required()
    page = page
    q_accounts = json.loads(request.get_json())
    # Setup pagination parameters
    page_max_count = 50
    page_count = page_max_count
    user_count = q_accounts.get("count", 0)
    if user_count and user_count <= 50:
        page_count = user_count

    # users = User.query.filter(User.user_role == UserRole.user).all()
    users = User.query.filter(User.user_role == UserRole.user).paginate(
        page=page,
        per_page=page_count,
        error_out=False,
        max_per_page=page_max_count,
    )
    # Set cursor for iterations
    cursor = {
        "requested_count": user_count,
        "actual_count": len(users.items),
        "current_page": page,
        "total_pages": users.pages,
        "has_remaining_data": users.has_next,
        "next_page": users.next_num,
    }
    in_data: list[dict] = []
    for user in users.items:
        ujson = json.loads(json.dumps(user, cls=CustomJSONEncoder))
        cjson = json.loads(
            json.dumps(user.configuration, cls=CustomJSONEncoder)
        )
        ujson["configuration"] = cjson
        in_data.append(ujson)
    return {
        "accounts": OutUser(partial=True, unknown="exclude", many=True).load(
            in_data
        ),
        "cursor": cursor,
    }, 200
