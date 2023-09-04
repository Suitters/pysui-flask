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

from pysui_flask import db
from pysui_flask.api.schema.account import OutUser, validate_public_key

# from flasgger import swag_from
from . import (
    account_api,
    User,
    UserRole,
    SignerStatus,
    SignatureStatus,
    SignatureTracking,
    SignatureRequest,
)
import pysui_flask.api.common as cmn
from pysui_flask.api_error import ErrorCodes, APIError
from pysui import SuiRpcResult, SuiAddress
from pysui.sui.sui_txn import SyncTransaction


def _user_login_required():
    if not session.get("user_logged_in"):
        raise APIError("User must login first", ErrorCodes.LOGIN_REQUIRED)


def post_signature_request(to_accounts: list[User], base64_txbytes: str):
    """."""
    tracker = SignatureTracking()
    tracker.status = SignatureStatus.pending_signers
    tracker.expected_signatures = len(to_accounts)
    tracker.completed_signatures = 0
    db.session.add(tracker)
    db.session.flush()
    for account in to_accounts:
        sig_r = SignatureRequest()
        sig_r.from_account = account.account_key
        sig_r.tx_byte_string = base64_txbytes
        sig_r.status = SignerStatus.pending
        sig_r.signing_tracker = tracker.id
        # Add to the user table
        account.sign_requests.append(sig_r)
        # Add to the session
        db.session.add(sig_r)
    db.session.commit()


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
    ujson = json.loads(json.dumps(user, cls=cmn.CustomJSONEncoder))
    ujson["configuration"] = json.loads(
        json.dumps(user.configuration, cls=cmn.CustomJSONEncoder)
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
        user: User = cmn.verify_credentials(
            username=in_data["username"],
            user_password=in_data["password"],
            expected_role=UserRole.user,
        )
        session["name"] = in_data["username"]
        session["user_key"] = user.account_key
        session["user_logged_in"] = True
    return {"session": session.sid}


@account_api.get("/logoff")
def account_logoff():
    """Verify account login."""
    _user_login_required()
    session.pop("name")
    session.pop("user_key")
    session.pop("user_logged_in")
    return {"session": f"{session.sid} ended"}


@account_api.post("/public_key")
def set_publickey():
    """Set my own public key."""
    _user_login_required()
    in_data = json.loads(request.get_json())
    user: User = User.query.filter(
        User.account_key == session["user_key"]
    ).one()
    if "public_key" in in_data:
        pk, addy = validate_public_key(in_data["public_key"])
        user.configuration.public_key = pk
        user.configuration.active_address = addy
        db.session.commit()
    return {"user_update": {"public_key": pk, "active_address": addy}}


@account_api.get("/gas")
def account_gas():
    """Fetch gas for account."""
    _user_login_required()
    client, _user = cmn.client_for_account_action(session["user_key"])
    in_data = json.loads(request.get_json())
    get_all = in_data.get("all", False)
    result = client.get_gas(None, get_all)
    if result.is_ok():
        return result.result_data.to_dict()
    raise APIError(
        f"Sui error {result.result_string}", ErrorCodes.SUI_ERROR_BASE
    )


@account_api.get("/objects")
def account_objects():
    """Fetch objects for account."""
    _user_login_required()
    client, _user = cmn.client_for_account_action(session["user_key"])
    in_data = json.loads(request.get_json())
    get_all = in_data.get("all", False)
    result = client.get_objects(None, get_all)
    if result.is_ok():
        return result.result_data.to_dict()
    raise APIError(
        f"Sui error {result.result_string}", ErrorCodes.SUI_ERROR_BASE
    )


@account_api.get("/object/<string:object_id>")
def account_object(object_id):
    """Fetch specific object by id."""
    _user_login_required()
    object_id = object_id
    cmn.validate_object_id(object_id, True)
    client, _user = cmn.client_for_account_action(session["user_key"])
    in_data = json.loads(request.get_json())
    result = client.get_object(object_id, in_data.get("version"))
    if result.is_ok():
        return result.result_data.to_dict()
    raise APIError(
        f"Sui error {result.result_string}", ErrorCodes.SUI_ERROR_BASE
    )


@account_api.get("/pysui_txn")
def account_inspect_or_validate_transaction():
    """Deserialize and inspect or validate transaction construct."""
    _user_login_required()
    client = cmn.client_for_account(session["user_key"])
    in_data = json.loads(request.get_json())
    tx_builder = in_data.get("tx_base64")
    perform = in_data.get("perform", "inspection")
    if tx_builder:
        txer: SyncTransaction = cmn.deser_transaction(client, tx_builder)
        if perform == "inspection":
            result = txer.inspect_all()
            if isinstance(result, SuiRpcResult):
                raise APIError(
                    f"Sui error {result.result_string}",
                    ErrorCodes.SUI_ERROR_BASE,
                )
            return result.to_dict()
        elif perform == "verification":
            _base_constr, error_rpt = txer.verify_transaction()
            return {"verification": error_rpt if error_rpt else "success"}

    raise APIError("Missing 'tx_base64' string", ErrorCodes.PYSUI_ERROR_BASE)


@account_api.post("/pysui_txn")
def account_execute_transaction():
    """Deserialize and execute builder construct."""
    _user_login_required()
    client, user = cmn.client_for_account_action(session["user_key"])
    signers: list[User] = [user]
    in_data = json.loads(request.get_json())
    tx_builder = in_data.get("tx_base64")
    verify = in_data.get("run_verification", False)
    gas_budget = in_data.get("gas_budget", "")
    gas_object = in_data.get("use_gas_object", None)
    sponsor_account_key = in_data.get("txn_sponsor", None)

    if tx_builder:
        txer = cmn.deser_transaction(client, tx_builder)
        try:
            # This user is the sender
            txer.signer_block.sender = SuiAddress(
                user.configuration.active_address
            )
            if sponsor_account_key:
                sponsor = User.query.filter(
                    User.account_key == sponsor_account_key
                ).first()
                if not sponsor:
                    raise APIError(
                        f"Sponsor account with key: {sponsor_account_key} not found",
                        ErrorCodes.ACCOUNT_NOT_FOUND,
                    )
                else:
                    signers.append(sponsor)
            gas_object = (
                gas_object
                if (gas_object and cmn.validate_object_id(gas_object, True))
                else None
            )
            txdata_to_sign = txer.deferred_execution(
                run_verification=verify,
                use_gas_object=gas_object,
                gas_budget=gas_budget,
            )
            # This is temporary
            # Post to user sign requests
            # Flatten accounts to post to
            post_signature_request(cmn.flatten_users(signers), txdata_to_sign)
            # Post txdata to request table
            mlen = len(txdata_to_sign)
            return {"success": txdata_to_sign}
        except Exception as exc:
            raise APIError(
                f"Exception {exc.args[0]}", ErrorCodes.CONTENT_TYPE_ERROR
            )
    raise APIError("Missing 'tx_base64' string", ErrorCodes.PYSUI_ERROR_BASE)


@account_api.get("/signing_requests")
def get_signing_requests():
    """."""
    _user_login_required()
    user: User = User.query.filter(
        User.account_key == session["user_key"]
    ).first()
    return {
        "needs_signing": json.loads(
            json.dumps(user.sign_requests, cls=cmn.CustomJSONEncoder)
        )
    }, 200


@account_api.get("/multisig_requests")
def get_multisig_membership_requests():
    """."""
    _user_login_required()
    user: User = User.query.filter(
        User.account_key == session["user_key"]
    ).first()
    return {
        "needs_signing": json.loads(
            json.dumps(user.multisig_requests, cls=cmn.CustomJSONEncoder)
        )
    }, 200
