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
import pysui_flask.api.route.common as cmn
from pysui import SuiRpcResult

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


@account_api.get("/gas")
def account_gas():
    """Fetch gas for account."""
    _user_login_required()
    client = cmn.client_for_account(session["user_key"])
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
    client = cmn.client_for_account(session["user_key"])
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
    client = cmn.client_for_account(session["user_key"])
    in_data = json.loads(request.get_json())
    result = client.get_object(object_id, in_data.get("version"))
    if result.is_ok():
        return result.result_data.to_dict()
    raise APIError(
        f"Sui error {result.result_string}", ErrorCodes.SUI_ERROR_BASE
    )


@account_api.post("/pysui_txn")
def account_execute_from_builder():
    """Deserialize and execute builder construct."""
    _user_login_required()
    client = cmn.client_for_account(session["user_key"])
    in_data = json.loads(request.get_json())
    tx_builder = in_data.get("tx_base64")
    if tx_builder:
        txer = cmn.deser_transaction(client, tx_builder)
        try:
            result: SuiRpcResult = txer.execute()
            if result.is_err():
                raise APIError(
                    f"Sui error {result.result_string}",
                    ErrorCodes.SUI_ERROR_BASE,
                )
            return result.result_data.to_dict()
        except Exception as exc:
            raise APIError(
                f"Exception {exc.args[0]}", ErrorCodes.CONTENT_TYPE_ERROR
            )
    raise APIError("Missing 'tx_base64' string", ErrorCodes.PYSUI_ERROR_BASE)


@account_api.get("/pysui_txn")
def account_inspect_from_builder():
    """Deserialize and inspect construct."""
    _user_login_required()
    client = cmn.client_for_account(session["user_key"])
    in_data = json.loads(request.get_json())
    tx_builder = in_data.get("tx_base64")
    if tx_builder:
        txer = cmn.deser_transaction(client, tx_builder)
        result = txer.inspect_all()
        if isinstance(result, SuiRpcResult):
            raise APIError(
                f"Sui error {result.result_string}", ErrorCodes.SUI_ERROR_BASE
            )
        return result.to_dict()
    raise APIError("Missing 'tx_base64' string", ErrorCodes.PYSUI_ERROR_BASE)
