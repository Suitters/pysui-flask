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

import base64
import enum
import dataclasses
from datetime import datetime
import json
import hashlib
from typing import Optional, Union, Any
from flask import current_app
from pysui_flask.api.xchange.payload import TransactionIn, MultiSig
from pysui_flask.api_error import APIError, ErrorCodes
from pysui_flask.db_tables import (
    User,
    SigningAs,
    MultiSignature,
    MultiSigStatus,
)
from pysui import SyncClient, SuiConfig, SuiAddress
from pysui.sui.sui_crypto import SuiPublicKey, BaseMultiSig, SignatureScheme
from pysui.sui.sui_types.address import valid_sui_address
from pysui.sui.sui_txn import SyncTransaction, SigningMultiSig


def client_for_account(
    account_key: str, user: Optional[User] = None
) -> SyncClient:
    """Construct a client from a user account configuration."""
    user = user or User.query.filter(User.account_key == account_key).one()
    if user:
        try:
            cfg = SuiConfig.user_config(
                rpc_url=current_app.config["RPC_URL"],
            )
            cfg.set_active_address(SuiAddress(user.active_address))
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
    """Construct client with intent of executing a pysui action.

    :param account_key: Requestinig account used to construct connection with
    :type account_key: str
    :raises APIError: If no active-address, due to not having public key, available
    :raises APIError: Can not find account key
    :return: A tuple of the pysui client and the user record from db
    :rtype: tuple[SyncClient, User]
    """
    user: User = User.query.filter(User.account_key == account_key).one()
    if user:
        if not user.active_address:
            raise APIError(
                f"Account {account_key} does not have active address registered.",
                ErrorCodes.PYSUI_MISSING_PUBLIC_KEY,
            )
        return client_for_account(account_key, user), user
    raise APIError(
        f"Account with key: {account_key} not known",
        ErrorCodes.ACCOUNT_NOT_FOUND,
    )


def deser_transaction(client: SyncClient, txb_base64: str) -> SyncTransaction:
    """Construct a generic transaction builder."""
    return SyncTransaction(client, deserialize_from=txb_base64)


def ready_transaction(
    client: SyncClient, ctx: TransactionIn
) -> SyncTransaction:
    """Deserialize the transaction builder.

    :param client: The pysui client
    :type client: SyncClient
    :param ctx: The payload containing the serialized transaction builder
    :type ctx: TransactionIn
    :return: A synchronous pysui Transaction with TransactionBuilder
    :rtype: SyncTransaction
    """
    sync_tx = deser_transaction(client, ctx.tx_builder)

    return sync_tx


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
    """Convert a string to 32 byte hash."""
    encoded_pwd = str.encode(indata)
    return hashlib.blake2b(encoded_pwd, digest_size=32).hexdigest()


def verify_credentials(
    *,
    username: str,
    user_password: str,
) -> Union[User, APIError]:
    """Verifies credentials match database for user.

    :param user_name: Submitted name
    :type user_name: str
    :param user_password: Submitted password
    :type user_password: str
    :raises CredentialError: If username or password lengths are invalid
    :raises CredentialError: If failure to resolve user based on passed in credentials
    :return: The User account row from DB
    :rtype: User
    """
    # Find user
    result: User = User.query.filter(User.user_name == username).first()
    # Verify credentials
    if result:
        pwd_hashed = str_to_hash_hex(user_password)
        if pwd_hashed == result.password:
            return result
    raise APIError(
        f"Unable to verify credentials for {username}",
        ErrorCodes.CREDENTIAL_ERROR,
    )


@dataclasses.dataclass
class MultiSigRes:
    """MultiSigRes contains resolved user instances.

    Optional msig_signers identifies member subset
    """

    # This is the resolved base mutisig row
    msig_account: MultiSignature
    # Optionally these are account_keys for the msig members who are
    # required to sign. If None, all members must sign
    msig_signers: Optional[list[User]] = None


@dataclasses.dataclass
class SignersRes:
    """SignersRes contains user objects.

    If both sender and sponsor are None, the requestor is only signer.
    """

    requestor: User
    # Can be multi-sig, single account or None (default to requestor)
    sender: Optional[Union[MultiSigRes, User]] = None
    # Can be multi-sig, single account or None (default to requestor)
    sponsor: Optional[Union[MultiSigRes, User]] = None

    @property
    def sender_account(self) -> Union[str, None]:
        """Return the account key of the sender.

        This may be None.
        :return: The primary account key
        :rtype: Union[str, None]
        """
        if self.sender:
            return (
                self.sender.account_key
                if isinstance(self.sender, User)
                else self.sender.msig_account.owner_id
            )
        return None

    @property
    def senders(self) -> list[User]:
        """Returns list of one or more senders.

        If sender is None, use requestor

        :return: _description_
        :rtype: list[User]
        """
        if self.sender:
            return (
                [self.sender]
                if isinstance(self.sender, User)
                else self.sender.msig_signers
            )
        return [self.requestor]

    @property
    def sponsor_account(self) -> Union[str, None]:
        """Return the account key of the sponsor.

        :return: _description_
        :rtype: Union[str, None]
        """
        if self.sponsor:
            return (
                self.sponsor.account_key
                if isinstance(self.sponsor, User)
                else self.sponsor.msig_account.owner_id
            )
        return None

    @property
    def sponsors(self) -> list[User]:
        """Returns list of one or more senders.

        If sender is None, use requestor

        :return: _description_
        :rtype: list[User]
        """
        if self.sponsor:
            return (
                [self.sponsor]
                if isinstance(self.sponsor, User)
                else self.sponsor.msig_signers
            )
        return []


def construct_multisig(msig_acct: MultiSignature) -> BaseMultiSig:
    """Construct a pysui BaseMultiSig from db representation.

    :param msig_acct: The db construct (row)
    :type msig_acct: MultiSignature
    :raises ValueError: If the state of the db construct prevents construction
    :return: A pysui BaseMultiSig
    :rtype: BaseMultiSig
    """
    base_pkeys: list[SuiPublicKey] = []
    base_weights: list[int] = []
    if msig_acct.status == MultiSigStatus.confirmed:
        for member in msig_acct.multisig_members:
            # if member.status == Ms
            base_weights.append(member.weight)
            user: User = User.query.filter(
                User.account_key == member.owner_id
            ).one()
            pkb = base64.b64decode(user.configuration.public_key)
            base_pkeys.append(SuiPublicKey(SignatureScheme(pkb[0]), pkb[1:]))
        return BaseMultiSig(base_pkeys, base_weights, msig_acct.threshold)
    raise ValueError(
        f"{msig_acct.user.user_name_or_email} multisig state is not confirmed  {msig_acct.status.name}"
    )


def construct_sigblock_entry(sig_req: Union[User, MultiSigRes]) -> Any:
    """Create the signature block sender or sponsor for pysui Transaction."""
    # Straight forward user
    if isinstance(sig_req, User):
        return SuiAddress(sig_req.configuration.active_address)
    # Otherwise create the Base MultiSig
    base_msig = construct_multisig(sig_req.msig_account)

    # Create the signing multisig
    if sig_req.msig_signers:
        sig_pkeys: list[SuiPublicKey] = []
        for user in sig_req.msig_signers:
            pkb = base64.b64decode(user.configuration.public_key)
            for bpkey in base_msig.public_keys:
                if bpkey.key_bytes == pkb[1:]:
                    sig_pkeys.append(bpkey)
                    break
        if len(sig_pkeys) != len(sig_req.msig_signers):
            raise ValueError("Msig member mismatch")
    else:
        sig_pkeys = base_msig.public_keys
    return SigningMultiSig(base_msig, sig_pkeys)


def construct_sender(sig_req: SignersRes) -> Any:
    """Construct sender from requestor or provided explicit sender."""
    # FIXME: Assumes that the requestor is not multisig
    if not sig_req.sender:
        return SuiAddress(sig_req.requestor.configuration.active_address)
    return construct_sigblock_entry(sig_req.sender)


def _valid_account(acc_key: str) -> User:
    """."""
    user: User = User.query.filter(User.account_key == acc_key).one()
    if not user.active_address:
        raise APIError(f"Not a valid account", ErrorCodes.INVALID_ACCOUNT_ROLE)
    return user


# FIXME: Refactor for MultiSignature
def _valid_multisig_account(msig_acc: MultiSig) -> MultiSigRes:
    """."""
    msig_account = MultiSignature.query.filter(
        MultiSignature.multisig_name == msig_acc.msig_name
    ).one()
    # Have base
    msig_base: MultiSigRes = MultiSigRes(msig_account=msig_account)
    # If we specify subset signers, validate they exist
    # as members. Also, accumulate their weight
    if msig_acc.msig_signers:
        accum_weight = 0
        found = 0
        sub_signers: list[User] = []
        for member in msig_base.msig_account.multisig_members:
            if member.user.user_name in msig_acc.msig_signers:
                found += 1
                accum_weight += member.weight
                sub_signers.append(_valid_account(member.owner_id))

        # Did I find them all?
        if found != len(msig_acc.msig_signers):
            raise APIError(
                f"Invalid singing multisig members",
                ErrorCodes.PYSUI_INVALID_MS_MEMBER_KEY,
            )
        # Are their weights enough?
        elif accum_weight < msig_base.msig_account.threshold:
            raise APIError(
                f"MultiSig singer combined weight below threshold",
                ErrorCodes.PYSUI_MS_MEMBER_WEIGHT_BELOW_THRESHOLD,
            )
        # All good
        else:
            msig_base.msig_signers = sub_signers

    return msig_base


def _validate_signer(signer: Union[str, MultiSig]) -> Union[User, MultiSigRes]:
    """."""
    # Signer may be a user or multisig.
    if isinstance(signer, str):
        return _valid_account(signer)
    # If multisig and no msig_signers than defaults to all members sign
    # else check that the msig_signers are valid members
    if isinstance(signer, MultiSig):
        return _valid_multisig_account(signer)


def verify_tx_signers_existence(
    *, requestor: str, payload: TransactionIn
) -> Union[SignersRes, APIError]:
    """."""
    sig_res = SignersRes(requestor=_valid_account(requestor))
    # If the payload has no signers, requestor is signer and inferred sponsor
    if payload.have_signers:
        # If the sender signer is not None, it must be a valid account_key
        if payload.signers.sender:
            sig_res.sender = _validate_signer(payload.signers.sender)

        # If the sponsor signer is not None, it must be a valid account_key
        if payload.signers.sponsor:
            sig_res.sponsor = _validate_signer(payload.signers.sponsor)
    return sig_res


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
