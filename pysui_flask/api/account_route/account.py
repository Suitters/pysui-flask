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
import base64
import json
from typing import Any, Union

# from http import HTTPStatus
from flask import Blueprint, session, request

from pysui_flask import db

# from pysui_flask.api.xchange.account import OutUser, validate_public_key

# from flasgger import swag_from
from . import (
    account_api,
    User,
    UserRole,
    SigningAs,
    SignerStatus,
    SignatureStatus,
    SignatureTrack,
    SignatureRequest,
)
import pysui_flask.api.common as cmn
from pysui_flask.api_error import ErrorCodes, APIError
from pysui_flask.api.xchange.payload import *
from pysui_flask.api.xchange.account import OutUser, validate_public_key
from pysui_flask.api.signing import signature_update
from pysui import SuiRpcResult, SuiAddress
from pysui.sui.sui_txn import SyncTransaction, SigningMultiSig
from pysui.sui.sui_crypto import BaseMultiSig, SuiPublicKey


def _user_login_required():
    if not session.get("user_logged_in"):
        raise APIError("User must login first", ErrorCodes.LOGIN_REQUIRED)


def post_signature_request(
    sig_set: cmn.SignersRes,
    base64_txbytes: str,
) -> list[str]:
    """Create signature requests for transaction.

    :param sig_set: Construct that lays out sender and sponsor signing users/accounts
    :type sig_set: cmn.SignersRes
    :param base64_txbytes: The transaction bytes to be signed
    :type base64_txbytes: str
    :return: List of account keys that will sign
    :rtype: list[str]
    """
    tracker = SignatureTrack()
    tracker.tx_bytes = base64_txbytes
    # Explicit keys used in resolving final signatures
    tracker.explicit_sender = sig_set.sender_account
    tracker.explicit_sponsor = sig_set.sponsor_account
    tracker.status = SignatureStatus.pending_signers
    accounts_notified: list[str] = []
    # sigs: list[SignatureRequest] = []
    # Get sending account(s)
    for sender in sig_set.senders:
        sig_r = SignatureRequest()
        # Who is indtended to sign (can include the originator as sender)
        sig_r.signer_account_key = sender.account_key
        # Public key of signer
        sig_r.signer_public_key = sender.configuration.public_key
        # TODO: Are they sender or sponsoring
        sig_r.signing_as = SigningAs.tx_sender
        # These are control fields
        sig_r.status = SignerStatus.pending
        sig_r.signature = ""
        tracker.requests.append(sig_r)
        # sigs.append(sig_r)
        accounts_notified.append(sender.account_key)

    # Get sending account(s)
    for sponsor in sig_set.sponsors:
        sig_r = SignatureRequest()
        # Who is indtended to sign (can include the originator as sender)
        sig_r.signer_account_key = sponsor.account_key
        # Public key of signer
        sig_r.signer_public_key = sponsor.configuration.public_key
        # TODO: Are they sender or sponsoring
        sig_r.signing_as = SigningAs.tx_sponsor
        # These are control fields
        sig_r.status = SignerStatus.pending
        sig_r.signature = ""
        tracker.requests.append(sig_r)
        # sigs.append(sig_r)
        accounts_notified.append(account.account_key)

    # tracker.requests = sigs
    sig_set.requestor.sign_track.append(tracker)
    db.session.commit()
    return accounts_notified


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
    # Can not change if part of multisig
    if user.user_role == UserRole.multisig or user.multisig_member:
        raise APIError(
            f"{session['user_key']} is part of multisig, can't change public key",
            ErrorCodes.PUBLICKEY_MULTISIG_MEMBER,
        )
    # Can not change if has signature associations
    if _requested_filtered(session["user_key"], SignRequestFilter()):
        raise APIError(
            f"{session['user_key']} has signature requests",
            ErrorCodes.PUBLICKEY_SIGNATURES_EXIST,
        )
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
def account_submit_transaction():
    """Deserialize and execute builder construct."""
    _user_login_required()
    try:
        payload: TransactionIn = TransactionIn.from_json(request.get_json())
    except Exception as exc:
        raise APIError(f"{exc.args[0],ErrorCodes.PAYLOAD_ERROR}")
    # Verify signatures and return user model
    sig_req: cmn.SignersRes = cmn.verify_tx_signers_existence(
        requestor=session["user_key"], payload=payload
    )
    client, user = cmn.client_for_account_action(session["user_key"])

    txer = cmn.deser_transaction(client, payload.tx_builder)
    try:
        # Setup sender
        txer.signer_block.sender = cmn.construct_sender(sig_req)
        # Optional setup sponsor
        if sig_req.sponsor:
            txer.signer_block.sponsor = cmn.construct_sigblock_entry(
                sig_req.sponsor
            )
        # TODO:
        # Verify objects in builder are owned

        # Generate the tx_data (serialized as base64)
        txdata_to_sign = txer.deferred_execution(
            run_verification=payload.verify,
            use_gas_object=(
                payload.gas_object
                if (
                    payload.gas_object
                    and cmn.validate_object_id(payload.gas_object, True)
                )
                else None
            ),
            gas_budget=payload.gas_budget,
        )
        # Post to user sign requests
        requests_submitted = post_signature_request(sig_req, txdata_to_sign)
        return {"accounts_posted": requests_submitted}, 201
    except Exception as exc:
        raise APIError(
            f"Exception {exc.args[0]}", ErrorCodes.CONTENT_TYPE_ERROR
        )


def _requested_filtered(
    acct_key: str, payload: SignRequestFilter
) -> list[SignatureRequest]:
    """."""
    sign_as: list[SigningAs] = []
    status_is: list[SignerStatus] = []
    if payload.signing_as:
        if payload.signing_as.lower() == "sender":
            sign_as.append(SigningAs.tx_sender)
        elif payload.signing_as.lower() == "sponsor":
            sign_as.append(SigningAs.tx_sponsor)
    else:
        sign_as.extend([SigningAs.tx_sender, SigningAs.tx_sponsor])

    if payload.pending or payload.signed or payload.denied:
        if payload.pending:
            status_is.append(SignerStatus.pending)
        if payload.signed:
            status_is.append(SignerStatus.signed)
        if payload.denied:
            status_is.append(SignerStatus.denied)
    else:
        status_is.extend(
            [
                SignerStatus.pending,
                SignerStatus.signed,
                SignerStatus.denied,
            ]
        )
    return SignatureRequest.query.filter(
        SignatureRequest.signer_account_key == acct_key,
        SignatureRequest.signing_as.in_(sign_as),
        SignatureRequest.status.in_(status_is),
    ).all()


@account_api.get("/signing_requests")
def get_signing_requests():
    """."""
    _user_login_required()
    requests: list[SignatureRequest] = _requested_filtered(
        session["user_key"], SignRequestFilter.from_json(request.get_json())
    )
    # For each request, we need to grab the tx_bytes from the
    # tracker of the request and drop a few fields
    requests_enhanced: list[dict] = []
    for requested in requests:
        jsc = json.loads(json.dumps(requested, cls=cmn.CustomJSONEncoder))
        jsc["tx_bytes"] = requested.signature_track.tx_bytes
        jsc.pop("tracking")
        jsc.pop("signature")
        jsc.pop("signer_account_key")
        requests_enhanced.append(jsc)

    return {"signing_requests": json.loads(json.dumps(requests_enhanced))}, 200


@account_api.post("/signing_request")
def set_signing_requests():
    """."""
    _user_login_required()
    try:
        payload: SigningResponse = SigningResponse.from_json(
            request.get_json()
        )
        result = signature_update(
            session_key=session["user_key"], sig_resp=payload
        )
        action_taken = {"signature_response": result}
        return action_taken, 201

    except Exception as exc:
        raise APIError(f"{exc.args[0],ErrorCodes.PAYLOAD_ERROR}")


@account_api.get("/pysui_get_txn")
def get_transaction_results():
    """Get transactions the account is in context of."""
    _user_login_required()
    tx_filter: TransactionFilter = TransactionFilter.from_json(
        request.get_json()
    )
    requests: list[SignatureRequest] = _requested_filtered(
        session["user_key"], tx_filter.request_filter
    )
    tx_result: list[dict] = []
    # Result is:
    # {"transactions":[{"track":tsc,"signers":[dict],"results":dict}]}
    # For each request, get the tracker and go top down
    for ireq in requests:
        track: SignatureTrack = SignatureTrack.query.filter(
            SignatureTrack.id == ireq.tracking
        ).one()
        data_point = {
            "track": json.loads(json.dumps(track, cls=cmn.CustomJSONEncoder)),
            "signers": [
                json.loads(json.dumps(x, cls=cmn.CustomJSONEncoder))
                for x in track.requests
            ],
            "result": json.loads(
                json.dumps(track.execution, cls=cmn.CustomJSONEncoder)
            ),
        }
        tx_result.append(data_point)
    return {"transactions": json.loads(json.dumps(tx_result))}, 200


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
