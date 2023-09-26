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
import hashlib
from dataclasses import dataclass
from typing import Optional, Union
from dataclasses_json import dataclass_json
from marshmallow import (
    Schema,
    fields,
    validate,
    pre_load,
    exceptions,
    post_load,
)
from pysui import SuiAddress
from pysui.abstracts.client_keypair import SignatureScheme
from pysui.sui.sui_constants import SUI_HEX_ADDRESS_STRING_LEN


def _public_key_for_base64(
    *, wallet_key: str, key_scheme: str
) -> tuple[str, str]:
    """Validate and convert to public key Sui string."""
    pub_key_bytes = base64.b64decode(wallet_key)
    key_scheme = key_scheme.upper()
    if key_scheme == "ED25519":
        if len(pub_key_bytes) == 32:
            ba = bytearray([0])
            ba.extend(pub_key_bytes)
            return (
                base64.b64encode(ba).decode(),
                SuiAddress.from_bytes(ba).address,
            )
    elif key_scheme == "SECP256K1" or key_scheme == "SECP256R1":
        if len(pub_key_bytes) == 33:
            ba = bytearray([1])
            ba.extend(pub_key_bytes)
            return (
                base64.b64encode(ba).decode(),
                SuiAddress.from_bytes(ba).address,
            )
    elif key_scheme == "SECP256R1":
        if len(pub_key_bytes) == 33:
            ba = bytearray([2])
            ba.extend(pub_key_bytes)
            return (
                base64.b64encode(ba).decode(),
                SuiAddress.from_bytes(ba).address,
            )
    exceptions.ValidationError(
        f"key_scheme {key_scheme} not valid keytype for account"
    )


def validate_public_key(in_pubkey) -> tuple[str, str]:
    """Validate public key."""
    if isinstance(in_pubkey, dict):
        base_keys = frozenset({"wallet_key", "key_scheme"})
        if not in_pubkey.keys() >= base_keys:
            raise ValueError(
                f"Wallet public key requires 'wallet_key' and 'key_scheme'"
            )
        pk, addy = _public_key_for_base64(**in_pubkey)
    # FIXME: Public key lengths differ
    elif isinstance(in_pubkey, str):
        if len(in_pubkey) == 44:
            pk = in_pubkey
            addy = SuiAddress.from_bytes(base64.b64decode(pk)).address
    return pk, addy


class UserIn(Schema):
    """Fields for user when requesting a new account in admin."""

    username = fields.Str(
        required=True, validate=validate.Length(min=4, max=254)
    )
    password = fields.Str(
        required=True, validate=validate.Length(min=8, max=16)
    )
    public_key = fields.Str(
        required=True,
        validate=validate.Length(min=44, max=48),
    )
    address = fields.Str(required=True, validate=validate.Length(equal=66))

    @pre_load
    def fix_inbounds(self, in_bound, **kwargs):
        """."""
        if isinstance(in_bound, dict) and in_bound:
            try:
                pk, addy = validate_public_key(in_bound["public_key"])
                in_bound["address"] = addy
                if len(pk) != 44:
                    pkl = len(pk)
                    print(pkl)
                in_bound["public_key"] = pk
            except Exception as exc:
                raise exceptions.ValidationError(exc.args[0])
        else:
            raise exceptions.ValidationError(
                f"Config expects a map with data found {in_bound}"
            )

        return in_bound


class AccountSetup(Schema):
    """Primary wrapper for account setup."""

    user = fields.Nested(UserIn, many=False, required=True)


# For performance
_setup_schema = AccountSetup(many=False)
_setup_schemas = AccountSetup(many=True)


class MultiSigMember(Schema):
    """Member list of multisig."""

    account_key = fields.Str(required=True, validate=validate.Length(equal=66))
    weight = fields.Int(
        required=True, strict=True, validate=validate.Range(min=1, max=255)
    )


class MultiSig(Schema):
    """Member list of multisig."""

    members = fields.List(fields.Nested(MultiSigMember), required=True)
    name = fields.Str(required=True, validate=validate.Length(min=4, max=254))
    threshold = fields.Int(
        required=True, strict=True, validate=validate.Range(min=1, max=2550)
    )
    requires_attestation = fields.Bool(
        required=False, allow_none=True, load_default=False
    )

    @post_load
    def member_check(self, item, many, **kwargs):
        """."""
        if len(item["members"]) > 10:
            raise exceptions.ValidationError(
                f"Max 10 multisig members allowed, found {len(item['members'])}"
            )
        if len(item["members"]) < 2:
            raise exceptions.ValidationError(
                f"Need at least 2 multisig members required, found {len(item['members'])}"
            )

        return item


class MultiSigSetup(Schema):
    """Primary wrapper for account setup."""

    # The msig user info
    account = fields.Nested(AccountSetup, many=False, required=True)
    # user = fields.Nested(UserIn, many=False, required=True)
    # the msig config
    # config = fields.Nested(Config, many=False, required=True)
    # the msig
    multi_sig = fields.Nested(MultiSig, many=False, required=True)


# For performance
_ms_setup_schema = MultiSigSetup(many=False)
_ms_setup_schemas = MultiSigSetup(many=True)


@dataclass_json
@dataclass
class InUser:
    """New user account dataclass."""

    username: str
    password: str
    public_key: Optional[str] = ""
    address: Optional[str] = ""


@dataclass_json
@dataclass
class InAccountSetup:
    """Container for new user account setup."""

    user: InUser


# For performance, build the schema for re-use
_in_account_setup = InAccountSetup.schema()


def deserialize_user_create(in_data: Union[dict, list]) -> InAccountSetup:
    """Deserialize inbound account data during user setup.

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


@dataclass_json
@dataclass
class InMultiSigMember:
    """."""

    account_key: str
    weight: int


@dataclass_json
@dataclass
class InMultiSig:
    """."""

    members: list[InMultiSigMember]
    threshold: int
    name: str
    requires_attestation: Optional[bool]


@dataclass_json
@dataclass
class InMultiSigSetup:
    """Container for new user account setup."""

    account: InAccountSetup
    # config: InConfig
    multi_sig: InMultiSig


# For performance, build the schema for re-use
_in_ms_account_setup = InMultiSigSetup.schema()


def deserialize_msig_create(in_data: Union[dict, list]) -> InMultiSigSetup:
    """Deserialize inbound multi-sig account data during setup.

    It is first passed through marshmallow for validation before
    converted to dataclasses.

    :param in_data: A dictionary of required and optional keywords
    :type in_data: dict | list
    :return: dataclass(es) for result data
    :rtype: InAccountSetup | list[InAccountSetup]
    """
    if isinstance(in_data, dict):
        return InMultiSigSetup.from_dict(in_data)
    elif isinstance(in_data, list):
        outputs: list = _ms_setup_schemas.load(in_data)
        return [_in_ms_account_setup.load(x) for x in outputs]


class OutConfig(Schema):
    """Configuration setting dataclass for new account."""

    rpc_url = fields.Str()
    public_key = fields.Str()
    active_address = fields.Str()
    ws_url = fields.Str()


class OutUser(Schema):
    """New user account dataclass."""

    user_name = fields.Str()
    account_key = fields.Str()
    public_key = fields.Str()
    active_address = fields.Str()
    creation_date = fields.Str()
    configuration = fields.Nested(OutConfig, many=False, unknown="exclude")


if __name__ == "__main__":
    good_content = [
        {
            "account": {
                "user": {
                    "username": "FrankC0",
                    "password": "Oxnard Gimble",
                    # "public_key": "AIUPxQveY18QxhDDdTO0D0OD6PNV+et50068d1g/rIyl",
                    "public_key": {
                        "key_scheme": "ED25519",
                        "wallet_key": "qo8AGl3wC0uqhRRAn+L2B+BhGpRMp1UByBi8LtZxG+U=",
                    },
                    # "environment": "devnet",
                },
            },
            "multi_sig": {
                "members": [
                    {
                        "account_key": "0x489e24d1b1adbbdb52d89dd83ba60f4943c0029ad314fa281b3ef1842c2c9580",
                        "weight": 1,
                    },
                    {
                        "account_key": "0x489e24d1b1adbbdb52d89dd83ba60f4943c0029ad314fa281b3ef1842c2c9580",
                        "weight": 1,
                    },
                ],
                "threshold": 2,
                "name": "FrankC0",
                "requires_attestation": True,
            },
        }
    ]
    x = deserialize_msig_create(good_content)
    print(x)
    # print(x.to_json(indent=2))
    # print(_ms_setup_schema.load(good_content))
