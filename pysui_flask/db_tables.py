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

"""Database table set."""

import dataclasses
import enum
from datetime import datetime

from . import db

# from flask.json import JSONEncoder


class UserRole(enum.Enum):
    """Extend as needed."""

    admin = 1
    user = 2
    multisig = 3


class SignatureStatus(enum.Enum):
    """Extend as needed."""

    pending_signers = 1  # When all signers pending
    partially_completed = 2  # When not all have signed yet
    denied = 3  # If any one has denied
    signed = 4  # When all signed
    signed_and_executed = 5  # When already executed


class SignerStatus(enum.Enum):
    """Extend as needed."""

    pending = 1  # Waiting for signature
    signed = 2  # Signed, ready to go
    denied = 3  # Rejected signing


class SigningAs(enum.Enum):
    """Extend as needed."""

    tx_sender = 1  # Am I being asked to sign as sender or sponsor (both if no sponsor identified)
    tx_sponsor = 2  # Am I being asked to sign and pay for transaction


class MultiSigStatus(enum.Enum):
    """Extend as needed."""

    pending_attestation = 1
    confirmed = 2
    denied = 3
    invalid = 4


class MsMemberStatus(enum.Enum):
    """Extend as needed."""

    request_attestation = 1
    confirmed = 2
    denied = 3
    dropped = 4


@dataclasses.dataclass
class User(db.Model):
    """User table contains indicative data and keys."""

    id: int = db.Column(
        "user_id",
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )
    # Auto generated... this is not the private key of account
    account_key: str = db.Column(db.String(44), nullable=False)
    # One way hashed value from password text
    password: str = db.Column(db.String(64), nullable=False)
    # user email or string, must be unique clear
    user_name_or_email: str = db.Column(db.String(254), nullable=False)
    # Encode a role
    user_role: int = db.Column(db.Enum(UserRole), nullable=False)
    # When registered
    creation_date: datetime = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow
    )
    # May or may not have a configuration
    configuration = db.relationship(
        "UserConfiguration",
        backref="user",
        lazy=True,
        uselist=False,
        cascade="all, delete-orphan",
    )
    # May or may not have a multisig config
    multisig_configuration = db.relationship(
        "MultiSignature",
        backref="user",
        lazy=True,
        uselist=False,
        cascade="all, delete-orphan",
    )
    # May or may not be a member of multisig
    multisig_member = db.relationship(
        "MultiSigMember",
        backref="user",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )
    # May or may not have multi-sig join requests
    multisig_requests = db.relationship(
        "MultiSigRequest",
        backref="user",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )
    # May or may not have signing requests
    sign_track = db.relationship(
        "SignatureTrack",
        backref="user",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )


@dataclasses.dataclass
class UserConfiguration(db.Model):
    """Configuration for instantiating SuiConfig for User."""

    id: int = db.Column(
        "configuration_id",
        db.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    # Owner (user) ID relationship
    owner_id: str = db.Column(
        db.String, db.ForeignKey("user.account_key"), nullable=False
    )
    # Urls
    rpc_url: str = db.Column(db.String(254), nullable=False)
    ws_url: str = db.Column(db.String(254), nullable=True)
    # Addresses and keys
    # The active_address gets set when a multisig is built
    public_key: str = db.Column(db.String(44), nullable=True)
    active_address: str = db.Column(db.String(66), nullable=True)


# Multi-Sig


@dataclasses.dataclass
class MultiSignature(db.Model):
    """MultiSignature base."""

    id: int = db.Column(
        "multisig_id",
        db.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    # Account (user) owner ID of the MultiSig
    owner_id: str = db.Column(
        db.String, db.ForeignKey("user.account_key"), nullable=False
    )
    status: int = db.Column(db.Enum(MultiSigStatus), nullable=False)
    # Contains one or more members
    multisig_members = db.relationship(
        "MultiSigMember",
        backref="multi_signature",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )
    threshold: int = db.Column(db.Integer, nullable=False)


@dataclasses.dataclass
class MultiSigMember(db.Model):
    """MultiSignature base member."""

    id: int = db.Column(
        "ms_member_id",
        db.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    # Owner (user) ID of the MultiSig
    ms_owner_id: str = db.Column(
        db.String, db.ForeignKey("multi_signature.multisig_id"), nullable=False
    )
    # Owner (user) ID of the account
    owner_id: str = db.Column(
        db.String, db.ForeignKey("user.account_key"), nullable=False
    )
    weight: int = db.Column(db.Integer, nullable=False)
    position: int = db.Column(db.Integer, nullable=False)
    status: int = db.Column(db.Enum(MsMemberStatus), nullable=False)


# Request queues


@dataclasses.dataclass
class MultiSigRequest(db.Model):
    """MultiSignature base member requesst queue."""

    id: int = db.Column(
        "ms_request_id",
        db.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    # The user/account the request is for
    member_id: str = db.Column(
        db.String, db.ForeignKey("user.account_key"), nullable=False
    )
    # This is the account that made the request
    membership_key: str = db.Column(db.String(44), nullable=False)


@dataclasses.dataclass
class SignatureTrack(db.Model):
    """Signature tracking table."""

    id: int = db.Column(
        "sig_track_id",
        db.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    # Likley this is also the intended signer account
    requestor: str = db.Column(
        db.String, db.ForeignKey("user.account_key"), nullable=False
    )
    # Tracks requests
    requests = db.relationship(
        "SignatureRequest",
        backref="signature_track",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )
    # Tracks Execution
    execution = db.relationship(
        "TransactionResult",
        backref="signature_track",
        lazy=True,
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Set when either are not requestor
    explicit_sender: str = db.Column(db.String(44), nullable=True)
    explicit_sponsor: str = db.Column(db.String(44), nullable=True)

    # This is the tx_byte base64 string that requires signing
    tx_bytes: str = db.Column(db.String(200000), nullable=False)
    # Status
    status: int = db.Column(db.Enum(SignatureStatus), nullable=False)


@dataclasses.dataclass
class SignatureRequest(db.Model):
    """Signature request queue.

    While tracking starts vis-a-vis the account that requested tx,
    In order for individual users to know what is pending for them this
    table is accessed directly.

    Some of this information as well as the tx_bytes and requestor info
    is shared with the response.

    Some portion of the below is returned with status and signature set (if signing not denied.)
    """

    id: int = db.Column(
        "sig_request_id",
        db.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    # This is backref to signtracker
    tracking: str = db.Column(
        db.String,
        db.ForeignKey("signature_track.sig_track_id"),
        nullable=False,
    )
    # Who is indtended to signer (can include the originator as sender)
    signer_account_key: str = db.Column(db.String(44), nullable=False)
    signer_public_key: str = db.Column(db.String(44), nullable=False)
    # Are they sender or sponsoring
    signing_as: int = db.Column(db.Enum(SigningAs), nullable=False)
    # Control fields
    status: int = db.Column(db.Enum(SignerStatus), nullable=False)
    signature: str = db.Column(db.String(2048), nullable=True)


@dataclasses.dataclass
class TransactionResult(db.Model):
    """Transaction tracking table."""

    id: int = db.Column(
        "txn_id",
        db.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    # This is backref to signtracker
    tracking: str = db.Column(
        db.String,
        db.ForeignKey("signature_track.sig_track_id"),
        nullable=False,
    )
    transaction_passed: bool = db.Column(db.Boolean, nullable=False)
    transaction_response: str = db.Column(db.String(10240), nullable=False)
