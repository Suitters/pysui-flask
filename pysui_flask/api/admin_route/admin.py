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

from pysui_flask.db_tables import (
    db,
    AccountStatus,
    User,
    MultiSigMember,
    MultiSignature,
    MsMemberStatus,
    MultiSigStatus,
)
from . import admin_api, admin_login_required, APIError, ErrorCodes
import pysui_flask.api.common as cmn

from pysui_flask.api.xchange.payload import (
    InAccountSetup,
    InMultiSig,
    OutUser,
    deserialize_user_create,
    deserialize_msig_create,
)

from pysui.sui.sui_crypto import (
    create_new_keypair,
    SuiPublicKey,
    BaseMultiSig,
    SignatureScheme,
)


def _content_expected(fields):
    raise APIError(f"Expected {fields} in request", ErrorCodes.REQUEST_CONTENT_ERROR)


@admin_api.get("/")
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
        pwd_hashed = cmn.str_to_hash_hex(in_data["password"])
        if (
            current_app.config["ADMIN_PASSWORD"] == pwd_hashed
            and current_app.config["ADMIN_NAME"] == in_data["username"]
        ):
            session["name"] = in_data["username"]
            session["admin_logged_in"] = True
        else:
            raise APIError(
                f"Unable to verify credentials for {in_data['username']}",
                ErrorCodes.CREDENTIAL_ERROR,
            )
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
        user.user_name = user_config.user.username
        # Specifics to user in current blockchain network
        user.public_key = user_config.user.public_key
        user.active_address = user_config.user.address
        # Add and commit
        db.session.add(user)
        users.append(user)
    if not defer_commit:
        db.session.commit()

    return users


def _new_msig_reg(
    *,
    msig_configs: list[InMultiSig],
) -> list[MultiSignature]:
    """Process one or more multisig user accounts.

    :param msig_configs: List of one or more MultiSig registration requests
    :type msig_configs: list[InMultiSigSetup]
    :param defer_commit: Construct potential user account, defaults to False
    :type defer_commit: Optional[bool], optional
    :raises APIError: Multisig member account_key is not a valid user
    :return: _description_
    :rtype: list[User]
    """
    msig_results: list[MultiSignature] = []
    # Use with session and no interim flushing
    for index, ms_setup in enumerate(msig_configs):
        msig_entry: MultiSignature = MultiSignature()
        msig_entry.multisig_name = ms_setup.name
        msig_entry.threshold = ms_setup.threshold
        msig_entry.status = (
            MultiSigStatus.pending_attestation
            if ms_setup.requires_attestation
            else MultiSigStatus.confirmed
        )
        db.session.add(msig_entry)

        with db.session.no_autoflush:
            # Build the multisig constructs
            sig_keys = []
            sig_weights = []
            msig_members: list[MultiSigMember] = []
            for member in ms_setup.members:
                # Validate account for member exists
                user: User = User.query.filter(
                    User.active_address == member.active_address,
                ).first()
                # Build the member
                if user:
                    ms_member: MultiSigMember = MultiSigMember()
                    ms_member.position = len(msig_members)
                    ms_member.weight = member.weight
                    ms_member.status = (
                        MsMemberStatus.request_attestation
                        if msig_entry.status == MultiSigStatus.pending_attestation
                        else MsMemberStatus.confirmed
                    )
                    # For building a BaseMultiSig
                    pkb = base64.b64decode(user.public_key)
                    sig_keys.append(SuiPublicKey(SignatureScheme(pkb[0]), pkb[1:]))
                    sig_weights.append(ms_member.weight)
                    # Relationships
                    user.multisig_member.append(ms_member)
                    # msig_entry.multisig_members.append(ms_member)
                    msig_members.append(ms_member)

                else:
                    raise APIError(
                        f"Account is not a valid user account: {member.account_key}",
                        ErrorCodes.PYSUI_MS_MEMBER_NO_ACCOUNT,
                    )
            # Construct BaseMultiSig for address
            bmsig = BaseMultiSig(sig_keys, sig_weights, msig_entry.threshold)
            msig_entry.multisig_members.extend(msig_members)
            msig_entry.active_address = bmsig.address

            # Create the msig user account
            # msig_configs[index].active_address = bmsig.address
            msig_results.append(msig_entry)

    # Commit it all
    db.session.commit()
    return msig_results


@admin_api.post("/account")
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
            User.user_name.like(user_in.user.username),
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
            "user_name": user_persist[0].user_name,
            "account_key": user_persist[0].account_key,
        }
    }, 201


@admin_api.post("/multisig")
def new_multi_sig_account():
    """Admin registration of new msig account."""
    admin_login_required()
    try:
        # Deserialize
        msig_in: InMultiSig = deserialize_msig_create(json.loads(request.get_json()))
        msig: MultiSignature = MultiSignature.query.filter(
            MultiSignature.multisig_name == msig_in.name
        ).first()
    except marshmallow.ValidationError as ve:
        _content_expected(ve.messages)
    # When we have a user with username and User role, fail
    if msig:
        raise APIError(
            f"MultiSig {msig_in.name} already exists.",
            ErrorCodes.USER_ALREADY_EXISTS,
        )
    # Create the new multisig user, configuration and members
    msig_persist: list[MultiSignature] = _new_msig_reg(msig_configs=[msig_in])
    return {
        "created": {
            "status": f"{msig_persist[0].status}",
            "address": msig_persist[0].active_address,
        }
    }, 201


@admin_api.post("/accounts")
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
                User.user_name.like(x.user.username),
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
                "user_name": users_persist.user_name,
                "account_key": users_persist.account_key,
            }
        )
    return {"created": user_result}, 201


@admin_api.get("/account/<string:active_address>")
def query_user_account(active_address):
    """Get a user account by account active-address."""
    admin_login_required()
    user: User = cmn.get_account_for_address(active_address)
    if user:
        ujson = json.loads(json.dumps(user, cls=cmn.CustomJSONEncoder))
        ujson["configuration"] = json.loads(
            json.dumps(user.configuration, cls=cmn.CustomJSONEncoder)
        )
        return {
            "account": OutUser(partial=True, unknown="exclude", many=False).load(ujson)
        }, 200
    raise APIError(
        f"Account {active_address} not exist.",
        ErrorCodes.ACCOUNT_NOT_FOUND,
    )


@admin_api.get("/accounts", defaults={"page": 1})
@admin_api.get("/accounts/<int:page>")
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
    users = User.query.paginate(
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
        # cjson = json.loads(
        #     json.dumps(user.configuration, cls=cmn.CustomJSONEncoder)
        # )
        # ujson["configuration"] = cjson
        in_data.append(ujson)
    return {
        "accounts": OutUser(partial=True, unknown="exclude", many=True).load(in_data),
        "cursor": cursor,
    }, 200


@admin_api.post("/account/<string:active_address>/lock")
def lock_acount(active_address):
    """Lock user at account_key."""
    admin_login_required()
    user: User = cmn.get_account_for_address(active_address)
    if user:
        user.status = AccountStatus.locked
        db.session.commit()
        return {"account_locked": active_address}, 201
    else:
        raise APIError(
            f"Account with key: {active_address} not known",
            ErrorCodes.ACCOUNT_NOT_FOUND,
        )


@admin_api.post("/account/<string:active_address>/unlock")
def unlock_acount(active_address):
    """Unlock user at account_key."""
    admin_login_required()
    user: User = cmn.get_account_for_address(active_address)
    if user:
        user.status = AccountStatus.active
        db.session.commit()
        return {"account_unlocked": active_address}, 201
    else:
        raise APIError(
            f"Account with key: {active_address} not known",
            ErrorCodes.ACCOUNT_NOT_FOUND,
        )
