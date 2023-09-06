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

import enum
import dataclasses
from datetime import datetime
import json
import hashlib
from typing import Optional, Union
from pysui_flask.api_error import APIError, ErrorCodes
from pysui_flask.db_tables import User, UserRole, SigningAs
from pysui import SyncClient, SuiConfig, SuiAddress
from pysui.sui.sui_types.address import valid_sui_address
from pysui.sui.sui_txn import SyncTransaction


def client_for_account(
    account_key: str, user: Optional[User] = None
) -> SyncClient:
    """Construct a client from a user account configuration."""
    user = user or User.query.filter(User.account_key == account_key).one()
    # user: User = User.query.filter(User.account_key == account_key).one()
    if user:
        try:
            cfg = SuiConfig.user_config(
                rpc_url=user.configuration.rpc_url,
                prv_keys=[],
                ws_url=user.configuration.ws_url,
            )
            cfg.set_active_address(
                SuiAddress(user.configuration.active_address)
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


def client_for_account_action(account_key: str) -> tuple[SyncClient, User]:
    """."""
    user: User = User.query.filter(User.account_key == account_key).one()
    if user:
        if not user.configuration.active_address:
            raise APIError(
                f"Account {account_key} does not have public_key registered.",
                ErrorCodes.PYSUI_NO_PUBLIC_KEY,
            )
        return client_for_account(account_key, user), user
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


def str_to_hash_hex(indata: str) -> str:
    """."""
    encoded_pwd = str.encode(indata)
    return hashlib.blake2b(encoded_pwd, digest_size=32).hexdigest()


def verify_credentials(
    *,
    username: str,
    user_password: str,
    expected_role: UserRole = UserRole.user,
) -> Union[User, APIError]:
    """Verifies credentials match database for user.

    :param user_name: Submitted name
    :type user_name: str
    :param user_password: Submitted password
    :type user_password: str
    :param expected_role: The expected role set by route
    :type expected_role: UserRole
    :raises CredentialError: If username or password lengths are invalid
    :raises CredentialError: If failure to resolve user based on passed in credentials
    :return: The User row from DB
    :rtype: User
    """
    # Find user
    result: User = User.query.filter(
        User.user_name_or_email == username
    ).first()
    # Verify credentials
    if result:
        if result.user_role == expected_role:
            pwd_hashed = str_to_hash_hex(user_password)
            if pwd_hashed == result.password:
                return result
    raise APIError(
        f"Unable to verify credentials for {username}",
        ErrorCodes.CREDENTIAL_ERROR,
    )


class CustomJSONEncoder(json.JSONEncoder):  # <<-- Add this custom encoder
    """Custom JSON encoder for the DB classes."""

    def default(self, o):
        """."""
        if dataclasses.is_dataclass(
            o
        ):  # this serializes anything dataclass can handle
            return dataclasses.asdict(o)
        if isinstance(o, datetime):  # this adds support for datetime
            return o.isoformat()
        if isinstance(o, enum.Enum):
            return o.value
        return super().default(o)


def flatten_users(
    accounts: dict[str, User]
) -> Union[list[tuple[SigningAs, User]], APIError]:
    """Splay out all account references associated to sender and or sponsor of transactions.

    :param accounts: Identifies sender and possibly sponsor
    :type accounts: dict[str, User]
    :return: List of tuples identifying 'signing as' sender batch or sponsor
    :rtype: Union[list[tuple[SigningAs, User]], APIError]
    """
    result_list: list[tuple[SigningAs, User]] = []
    if accounts["sender"]:
        if accounts["sender"].user_role == UserRole.user:
            result_list.append((SigningAs.tx_sender, accounts["sender"]))
        elif accounts["sender"].user_role == UserRole.multisig:
            pass
    # TODO: This is exception
    else:
        pass
    if accounts["sponsor"]:
        if accounts["sponsor"].user_role == UserRole.user:
            result_list.append((SigningAs.tx_sponsor, accounts["sponsor"]))
        elif accounts["sender"].user_role == UserRole.multisig:
            pass
    return result_list
