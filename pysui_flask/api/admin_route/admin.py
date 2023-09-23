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

"""Administration primary routes module."""

import base64
from functools import partial
import json

# from http import HTTPStatus
from operator import is_not
from typing import Optional
from flask import session, request, current_app

# from flasgger import swag_from
import marshmallow
from sqlalchemy import and_

from pysui_flask import db
from . import (
    admin_api,
    User,
    UserRole,
    UserConfiguration,
    MultiSignature,
    MultiSigMember,
    MultiSigStatus,
    MsMemberStatus,
    admin_login_required,
)
import pysui_flask.api.common as cmn

from pysui_flask.api_error import APIError, ErrorCodes
from pysui_flask.api.xchange.account import (
    InAccountSetup,
    InMultiSigSetup,
    OutUser,
    deserialize_user_create,
    deserialize_msig_create,
)

from pysui import SuiAddress
from pysui.sui.sui_crypto import (
    create_new_keypair,
    SuiPublicKey,
    BaseMultiSig,
    SignatureScheme,
)


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
    admin_login_required()
    return {"session": session.sid}


@admin_api.get("/login")
def admin_login():
    """Admin login with credential check."""
    if not session.get("admin_logged_in"):
        in_data = json.loads(request.get_json())
        # Get the User object of the admin role
        # Throws exception
        user = cmn.verify_credentials(
            username=in_data["username"],
            user_password=in_data["password"],
        )
        session["name"] = in_data["username"]
        session["admin_logged_in"] = True
    return {"session": session.sid}


@admin_api.get("/logoff")
def account_logoff():
    """Verify account login."""
    admin_login_required()
    session.pop("name")
    session.pop("admin_logged_in")
    return {"session": f"{session.sid} ended"}


# Add user account - required admin logged in


def _new_user_reg(
    *,
    user_configs: list[InAccountSetup],
    defer_commit: Optional[bool] = False,
    for_role: Optional[UserRole] = UserRole.user,
) -> list[User]:
    """Process one or more new user registrations.

    :param user_configs: list of one or more new account registrations
    :type user_configs: list[InAccountSetup]
    :param defer_commit: Construct potential user account, defaults to False
    :type defer_commit: Optional[bool], optional
    :param for_role: The role to assign the account user, defaults to UserRole.user
    :type for_role: Optional[UserRole], optional
    :return: List of committed User accounts
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
        user.password = cmn.str_to_hash_hex(user_config.user.password)
        user.user_name_or_email = user_config.user.username
        user.user_role = for_role

        # Create the configuration
        cfg = UserConfiguration()
        cfg.rpc_url = user_config.config.urls.rpc_url
        cfg.ws_url = user_config.config.urls.ws_url
        cfg.public_key = user_config.config.public_key
        cfg.active_address = user_config.config.address
        # Create the relationship
        user.configuration = cfg
        # Add and commit
        db.session.add(user)
        users.append(user)
    if not defer_commit:
        db.session.commit()

    return users


def _new_msig_reg(
    *,
    msig_configs: list[InMultiSigSetup],
    defer_commit: Optional[bool] = False,
) -> list[User]:
    """Process one or more multisig user accounts.

    :param msig_configs: List of one or more MultiSig registration requests
    :type msig_configs: list[InMultiSigSetup]
    :param defer_commit: Construct potential user account, defaults to False
    :type defer_commit: Optional[bool], optional
    :raises APIError: Multisig member account_key is not a valid user
    :return: _description_
    :rtype: list[User]
    """
    msig_results: list[User] = []
    # Use with session and no interim flushing
    with db.session.no_autoflush:
        # Build the multisig constructs
        for index, ms_setup in enumerate(msig_configs):
            msig_entry: MultiSignature = MultiSignature()
            msig_entry.threshold = ms_setup.multi_sig.threshold
            msig_entry.status = (
                MultiSigStatus.pending_attestation
                if ms_setup.multi_sig.requires_attestation
                else MultiSigStatus.confirmed
            )
            sig_keys = []
            sig_weights = []
            msig_members: list[MultiSigMember] = []
            for member in ms_setup.multi_sig.members:
                # Validate account for member exists
                user: User = User.query.filter(
                    User.account_key == member.account_key,
                ).first()
                # Build the member
                if user and user.user_role == UserRole.user:
                    ms_member: MultiSigMember = MultiSigMember()
                    ms_member.position = len(msig_members)
                    ms_member.weight = member.weight
                    ms_member.status = (
                        MsMemberStatus.request_attestation
                        if msig_entry.status
                        == MultiSigStatus.pending_attestation
                        else MsMemberStatus.confirmed
                    )
                    # For building a BaseMultiSig
                    pkb = base64.b64decode(user.configuration.public_key)
                    sig_keys.append(
                        SuiPublicKey(SignatureScheme(pkb[0]), pkb[1:])
                    )
                    sig_weights.append(ms_member.weight)
                    # Relationships
                    user.multisig_member.append(ms_member)
                    msig_members.append(ms_member)

                else:
                    raise APIError(
                        f"Account is not a valid user account: {member.account_key}",
                        ErrorCodes.PYSUI_MS_MEMBER_NO_ACCOUNT,
                    )
            # Construct BaseMultiSig for address
            bmsig = BaseMultiSig(sig_keys, sig_weights, msig_entry.threshold)
            msig_entry.multisig_members.extend(msig_members)

            # Create the msig user account
            msig_configs[index].account.config.address = bmsig.address
            msig_user: list[User] = _new_user_reg(
                user_configs=[msig_configs[index].account],
                defer_commit=True,
                for_role=UserRole.multisig,
            )

            msig_user[0].multisig_configuration = msig_entry
            msig_results.append(msig_user[0])

    # Commit it all
    db.session.commit()
    return msig_results


@admin_api.post("/user_account")
def new_user_account():
    """Admin registration of new user account."""
    admin_login_required()
    try:
        # Deserialize
        user_in: InAccountSetup = deserialize_user_create(
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
    user_persist = _new_user_reg(user_configs=[user_in])
    return {
        "created": {
            "user_name": user_persist[0].user_name_or_email,
            "account_key": user_persist[0].account_key,
        }
    }, 201


@admin_api.post("/multi_sig_account")
def new_multi_sig_account():
    """Admin registration of new msig account."""
    admin_login_required()
    try:
        # Deserialize
        msig_in: InMultiSigSetup = deserialize_msig_create(
            json.loads(request.get_json())
        )
        # Check if user exists
        user = User.query.filter(
            and_(
                User.user_name_or_email.like(msig_in.account.user.username),
                User.user_role == UserRole.user,
            )
        ).first()
    except marshmallow.ValidationError as ve:
        _content_expected(ve.messages)
    # When we have a user with username and User role, fail
    if user:
        raise APIError(
            f"MultiSig {msig_in.account.user.username} already exists.",
            ErrorCodes.USER_ALREADY_EXISTS,
        )
    # Create the new multisig user, configuration and members
    msig_persist = _new_msig_reg(msig_configs=[msig_in])
    return {
        "created": {
            "user_name": msig_persist[0].user_name_or_email,
            "account_key": msig_persist[0].account_key,
        }
    }, 201


@admin_api.post("/user_accounts")
def new_user_accounts():
    """Admin registration of bulk new user account."""
    admin_login_required()
    try:
        # Deserialize
        users_in: InAccountSetup = deserialize_user_create(
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

    for users_persist in _new_user_reg(user_configs=users_in):
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
    admin_login_required()
    q_account = json.loads(request.get_json())

    user = User.query.filter(
        User.account_key == q_account["account_key"],
    ).first()
    if user:
        ujson = json.loads(json.dumps(user, cls=cmn.CustomJSONEncoder))
        ujson["configuration"] = json.loads(
            json.dumps(user.configuration, cls=cmn.CustomJSONEncoder)
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
    """Fetches all user accounts with role user or multisig (not admin)."""
    admin_login_required()
    page = page
    q_accounts = json.loads(request.get_json())
    # Setup pagination parameters
    page_max_count = current_app.config["CONSTRAINTS"].entries_per_page
    page_count = page_max_count
    user_count = q_accounts.get("count", 0)
    if user_count and user_count <= page_max_count:
        page_count = user_count

    # users = User.query.filter(User.user_role == UserRole.user).all()
    users = User.query.filter(User.user_role != UserRole.admin).paginate(
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
        ujson = json.loads(json.dumps(user, cls=cmn.CustomJSONEncoder))
        cjson = json.loads(
            json.dumps(user.configuration, cls=cmn.CustomJSONEncoder)
        )
        ujson["configuration"] = cjson
        in_data.append(ujson)
    return {
        "accounts": OutUser(partial=True, unknown="exclude", many=True).load(
            in_data
        ),
        "cursor": cursor,
    }, 200
