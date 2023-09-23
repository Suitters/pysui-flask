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
from pysui_flask.api.xchange.payload import TransactionIn, MultiSig
from pysui_flask.api_error import APIError, ErrorCodes
from pysui_flask.db_tables import User, UserRole, SigningAs, MultiSignature
from pysui import SyncClient, SuiConfig, SuiAddress
from pysui.sui.sui_crypto import SuiPublicKey, BaseMultiSig
from pysui.sui.sui_types.address import valid_sui_address
from pysui.sui.sui_txn import SyncTransaction, SigningMultiSig


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
    """."""
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
    """."""
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
    result: User = User.query.filter(
        User.user_name_or_email == username
    ).first()
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


def construct_sigblock_entry(sig_req: Union[User, MultiSigRes]) -> Any:
    """."""
    # Straight forward user
    if isinstance(sig_req, User):
        return SuiAddress(sig_req.configuration.active_address)
    # Otherwise create the Base MultiSig
    base_pkeys: list[SuiPublicKey] = []
    base_weights: list[int] = []
    for member in sig_req.msig_account.multisig_members:
        base_weights.append(member.weight)
        user: User = User.query.filter(
            User.account_key == member.owner_id
        ).one()
        pkb = base64.b64decode(user.configuration.public_key)
        base_pkeys.append(SuiPublicKey(pkb[0], pkb[1:]))
    base_msig = BaseMultiSig(
        base_pkeys, base_weights, sig_req.msig_account.threshold
    )

    # Create the signing multisig
    if sig_req.msig_signers:
        sig_pkeys: list[SuiPublicKey] = []
        for user in sig_req.msig_signers:
            pkb = base64.b64decode(user.configuration.public_key)
            sig_pkeys.append(SuiPublicKey(pkb[0], pkb[1:]))
    else:
        sig_pkeys = base_pkeys
    return SigningMultiSig(base_msig, sig_pkeys)


def construct_sender(sig_req: SignersRes) -> Any:
    """."""
    if not sig_req.sender:
        return SuiAddress(sig_req.requestor.configuration.active_address)
    return construct_sigblock_entry(sig_req.sender)


def _valid_account(acc_key: str) -> User:
    """."""
    user: User = User.query.filter(User.account_key == acc_key).one()
    if (
        user.user_role == UserRole.admin
        or not user.configuration.active_address
    ):
        raise APIError(f"Not a valid account", ErrorCodes.INVALID_ACCOUNT_ROLE)
    return user


def _valid_multisig_account(msig_acc: MultiSig) -> MultiSigRes:
    """."""
    user: User = _valid_account(msig_acc.msig_account)
    if user.user_role != UserRole.multisig or not user.multisig_configuration:
        raise APIError(
            f"Invalid multisig account", ErrorCodes.INVALID_ACCOUNT_ROLE
        )
    # Have base
    msig_base: MultiSigRes = MultiSigRes(
        msig_account=user.multisig_configuration
    )
    # If we specify subset signers, validate they exist
    # as members. Also, accumulate their weight
    if msig_acc.msig_signers:
        accum_weight = 0
        found = 0
        sub_signers: list[User] = []
        for member in msig_base.msig_account.multisig_members:
            if member.owner_id in msig_acc.msig_signers:
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
        elif accum_weight < msig_base.threshold:
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
