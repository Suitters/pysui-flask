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

"""Account schema module."""


import base64
import binascii
from dataclasses import dataclass, field
from typing import Optional, Union
from dataclasses_json import dataclass_json, config
from marshmallow import Schema, fields, validate, pre_load, exceptions
from pysui.abstracts.client_keypair import SignatureScheme
from pysui.sui.sui_constants import SUI_HEX_ADDRESS_STRING_LEN


SUI_STANDARD_URI: dict[str, dict[str, str]] = {
    "devnet": {
        "rpc_url": "https://fullnode.devnet.sui.io:443",
        "ws_url": "wss://fullnode.devnet.sui.io:443",
    },
    "testnet": {
        "rpc_url": "https://fullnode.testnet.sui.io:443",
        "ws_url": "wss://fullnode.testnet.sui.io:443",
    },
    "mainnet": {
        "rpc_url": "https://fullnode.mainnet.sui.io:443",
        "ws_url": "wss://fullnode.mainnet.sui.io:443",
    },
}


class UserIn(Schema):
    """Fields for user when requesting a new account in admin."""

    username = fields.Str(
        required=True, validate=validate.Length(min=4, max=254)
    )
    password = fields.Str(
        required=True, validate=validate.Length(min=8, max=16)
    )


class ExplicitUri(Schema):
    """Urls associated to the user account being added."""

    rpc_url = fields.Url(required=True)
    # ws_url = fields.Url(required=False)
    ws_url = fields.Str(
        required=False,
        # validate=validate.URL(schemes=["ws", "wss"]),
    )


def _key_for_wallet_key(*, wallet_key: str, key_scheme: str) -> str:
    """Validate and convert wallet key to Sui keystring."""
    if len(wallet_key) != SUI_HEX_ADDRESS_STRING_LEN:
        exceptions.ValidationError(
            f"wallet_key {len(wallet_key)} wrong, expected {SUI_HEX_ADDRESS_STRING_LEN}"
        )
    if wallet_key[0:2] != "0x" or wallet_key[0:2] != "0X":
        exceptions.ValidationError(
            "Expected wallet_key to have 0x or 0X prefix"
        )
    scheme = SignatureScheme[key_scheme]
    if scheme.value > 2:
        exceptions.ValidationError(
            f"key_scheme {key_scheme} not valid keytype for account"
        )
    keybytes = bytearray(scheme.value.to_bytes(1, "little"))
    keybytes.extend(binascii.unhexlify(wallet_key[2:]))
    return base64.b64encode(keybytes).decode()


class Config(Schema):
    """Configuration setting when adding new account."""

    private_key = fields.Str(required=True, validate=validate.Length(equal=44))
    urls = fields.Nested(ExplicitUri, many=False, required=True)

    @pre_load
    def fix_inbounds(self, in_bound, **kwargs):
        """."""
        if isinstance(in_bound, dict) and in_bound:
            if "environment" in in_bound and "urls" in in_bound:
                raise exceptions.ValidationError(
                    f"Specifying environment and urls is mutually exclusive"
                )
            if "environment" in in_bound:
                in_bound["urls"] = SUI_STANDARD_URI.get(
                    in_bound.pop("environment")
                )
            if isinstance(in_bound["private_key"], dict):
                base_keys = frozenset({"wallet_key", "key_scheme"})
                if not in_bound["private_key"].keys() >= base_keys:
                    raise exceptions.ValidationError(
                        f"Wallet key requires 'wallet_key' and 'key_scheme'"
                    )
                in_bound["private_key"] = _key_for_wallet_key(
                    **in_bound["private_key"]
                )
        else:
            raise exceptions.ValidationError(
                f"Config expects a map with data found {in_bound}"
            )

        return in_bound


class AccountSetup(Schema):
    """Primary wrapper for account setup."""

    user = fields.Nested(UserIn, many=False, required=True)
    config = fields.Nested(Config, many=False, required=True)


# For performance
_setup_schema = AccountSetup(many=False)
_setup_schemas = AccountSetup(many=True)


@dataclass_json
@dataclass
class InUser:
    """New user account dataclass."""

    username: str
    password: str


@dataclass_json
@dataclass
class InUri:
    """Url settings in user account dataclass."""

    rpc_url: str
    ws_url: Optional[str] = None


@dataclass_json
@dataclass
class InConfig:
    """Configuration setting dataclass for new account."""

    private_key: str
    urls: InUri


@dataclass_json
@dataclass
class InAccountSetup:
    """Container for new user account setup."""

    user: InUser
    config: InConfig


# For performance, build the schema for re-use
_in_account_setup = InAccountSetup.schema()


def deserialize_account_setup(in_data: Union[dict, list]) -> InAccountSetup:
    """_summary_ Deserialize inbound account data during user setup.

    It is first passed through marshmallow for validation before
    converted to dataclasses.

    :param in_data: A dictionary of required and optional keywords
    :type in_data: dict | list
    :return: dataclass(es) for result data
    :rtype: InAccountSetup | list[InAccountSetup]
    """
    if isinstance(in_data, dict):
        return _in_account_setup.load(_setup_schema.load(in_data))
    elif isinstance(in_data, list):
        outputs: list = _setup_schemas.load(in_data)
        return [_in_account_setup.load(x) for x in outputs]


if __name__ == "__main__":
    pass
