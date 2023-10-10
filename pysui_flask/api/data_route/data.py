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
from flask import current_app


from pysui_flask.db_tables import db, User, MultiSignature
from . import data_api
from pysui_flask.api_error import ErrorCodes, APIError
from pysui_flask.api.xchange.account import OutUser
import pysui_flask.api.common as cmn
from pysui import ObjectID

def _data_enabled():
    """Test for enablement or throw error."""
    if not current_app.config["CONSTRAINTS"].allow_anonymous_dataread:
        raise APIError("Data reading not enabled", ErrorCodes.PYSUI_ERROR_BASE)


@data_api.get("/<string:address>/gas")
def get_gas_for(address):
    """."""
    _data_enabled()
    client = cmn.client_for_address(address)
    result = client.get_gas(None, True)
    if result.is_ok():
        return {"gas": result.result_data.data}, 200
    else:
        return {"error": result.result_string}


@data_api.get("/<string:address>/objects")
def get_objects_for(address):
    """Returns Sui coin objects for address.

    :param address: A valid Sui address
    :type address: str
    :return: An array of objects, else empty array
    :rtype: list
    """
    _data_enabled()
    client = cmn.client_for_address(address)
    result = client.get_objects(None, True)
    if result.is_ok():
        return {"objects": result.result_data.data}, 200
    else:
        return {"error": result.result_string}

@data_api.get("/object/<string:object_id>")
def get_object_for(object_id):
    """Returns Sui object for object_id.

    :param object_id: A valid Sui object_id
    :type object_id: str
    :return: Information on the specific object
    :rtype: dict
    """
    _data_enabled()

    client = cmn.client_for_any()
    result = client.get_object(ObjectID(object_id))
    if result.is_ok():
        return {"object": result.result_data}, 200
    else:
        return {"error": result.result_string}

@data_api.get("/accounts")
def get_accounts():
    """Get all accounts: both users and multisigs.

    :return: A listing of all users and all multisigs
    :rtype: dict
    """
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
