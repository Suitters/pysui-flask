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
from flask import Blueprint, request, current_app
import marshmallow
from pysui_flask import db

from . import data_api, MultiSignature, User
from pysui_flask.api_error import ErrorCodes, APIError
from pysui_flask.api.xchange.account import OutUser
import pysui_flask.api.common as cmn

# Generic Sui


def _data_enabled():
    """Test for enablement or throw error."""
    if current_app.config["ALLOW_ANONYMOUS_DATA_READ"] == 0:
        raise APIError("Data reading not enabled", ErrorCodes.PYSUI_ERROR_BASE)


# @data_api.get("/gas/<string:address>")
# def get_gas(address):
#     """."""
#     _data_enabled()


# @data_api.get("/objects/<string:address>")
# def get_objects(address):
#     """."""
#     _data_enabled()


# @data_api.get("/account/<string:address>")
# def get_account_for(address):
#     """."""
#     _data_enabled()


@data_api.get("/accounts")
def get_accounts():
    """."""
    _data_enabled()
    users = OutUser(partial=True, unknown="exclude", many=True).load(
        [
            json.loads(json.dumps(x, cls=cmn.CustomJSONEncoder))
            for x in User.query.all()
        ]
    )
    msigs: list[dict] = []
    for msig in MultiSignature.query.all():
        msig_d = json.loads(json.dumps(msig, cls=cmn.CustomJSONEncoder))
        msig_m: list[dict] = []
        for member in msig.multisig_members:
            msig_m.append(
                json.loads(json.dumps(member, cls=cmn.CustomJSONEncoder))
            )
        msig_d["multisig_members"] = msig_m
        msigs.append(msig_d)
    return {
        "accounts": {
            "users": users,
            "multi_signatures": msigs,
        }
    }
