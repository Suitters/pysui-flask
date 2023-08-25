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

"""Common utilities for route management."""

from pysui_flask.api_error import APIError, ErrorCodes
from . import User, UserRole
from pysui import SyncClient, SuiConfig
from pysui.sui.sui_types.address import valid_sui_address
from pysui.sui.sui_txn import SyncTransaction


def client_for_account(account_key: str) -> SyncClient:
    """Construct a client from a user account configuration."""
    user: User = User.query.filter(User.account_key == account_key).one()
    if user:
        try:
            cfg = SuiConfig.user_config(
                rpc_url=user.configuration.rpc_url,
                prv_keys=[user.configuration.private_key],
                ws_url=user.configuration.ws_url,
            )
            return SyncClient(cfg)
        except Exception as exc:
            raise APIError(
                exc.args[0],
                ErrorCodes.PYSUI_ERROR_BASE,
            )
    raise APIError(
        f"Account with key: {account_key} not known",
        ErrorCodes.ACCOUNT_NOT_FOUND,
    )


def deser_transaction(client: SyncClient, txb_base64: str) -> SyncTransaction:
    """Construct a generic transaction builder."""
    return SyncTransaction(client, deserialize_from=txb_base64)


def validate_object_id(object_id: str, except_if_false: bool = False):
    """Validate the formedness of the object id."""
    if valid_sui_address(object_id):
        pass
    else:
        if except_if_false:
            raise APIError(
                f"Invalid object_id syntax: {object_id}",
                ErrorCodes.PYSUI_ERROR_BASE,
            )
