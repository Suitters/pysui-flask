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


class AccountStatus(enum.Enum):
    """Used on User accounts."""

    active = 1  # An active account
    locked = 2  # An account that is locked


class SignatureStatus(enum.Enum):
    """Tracker signature status."""

    pending_signers = 1  # All signers pending (initial state)
    partially_completed = 2  # At least 1 signature
    denied = 3  # If any one has denied, the entire transaction won't run
    signed = 4  # When all signed
    signed_and_executed = 5  # When signed and executed


class SignerStatus(enum.Enum):
    """Individual signature status."""

    pending = 1  # Waiting for signature
    signed = 2  # Signed, ready to go
    denied = 3  # Rejected signing


class SigningAs(enum.Enum):
    """Flags what each signature role is in transaction."""

    tx_sender = 1  # Am I being asked to sign as sender or sponsor (both if no sponsor identified)
    tx_sponsor = 2  # Am I being asked to sign and pay for transaction


class MultiSigStatus(enum.Enum):
    """Status of the creation of a multisig."""

    pending_attestation = 1  # When first created and requires member attestation
    confirmed = 2  # All members affirmed or creator confirmed on creation
    denied = 3  # At least 1 member denied participation
    invalid = 4  # If a member drops out of being a signer


class MsMemberStatus(enum.Enum):
    """Member of multisig status."""

    request_attestation = 1  # Requires affirmation by member
    confirmed = 2  # Member is confirmed either through affirmation or on creation
    denied = 3  # Member does not want to particpate
    dropped = 4  # Member has dropped out of multi-sig, making it invalid


class TemplateVisibility(enum.Enum):
    """Indicates visibility."""

    owned = 1  # This transaction template is exclusive to user account
    shared = 2  # This transaction template is available to all


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
    user_name: str = db.Column(db.String(254), nullable=False)
    # Addresses and keys
    public_key: str = db.Column(db.String(44), nullable=True)
    # The active_address is derived
    active_address: str = db.Column(db.String(66), nullable=True)

    # When registered
    creation_date: datetime = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow
    )
    status: int = db.Column(
        db.Enum(AccountStatus), nullable=False, default=AccountStatus.active
    )
    # May or may not be a member of multisig
    multisig_member = db.relationship(
        "MultiSigMember",
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
    # May or may not have templates
    templates = db.relationship(
        "Template",
        backref="user",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )


# Templates


@dataclasses.dataclass
class Template(db.Model):
    """Template container."""

    id: int = db.Column(
        "template_id",
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Name for template
    template_name: str = db.Column(db.String(64), nullable=False)

    # visibility
    template_visibility: int = db.Column(
        db.Enum(TemplateVisibility), nullable=False, default=TemplateVisibility.owned
    )

    # This is the SuiTransaction builder serialized string
    serialized_builder: str = db.Column(db.String(200000), nullable=False)

    template_overrides: str = db.Column(db.String, nullable=False)

    # Owner (user) ID of the account
    owner_id: str = db.Column(
        db.String, db.ForeignKey("user.account_key"), nullable=False
    )

    # May or may not have overrides
    overrides = db.relationship(
        "TemplateOverride",
        backref="template",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )


@dataclasses.dataclass
class TemplateOverride(db.Model):
    """Template override position."""

    id: int = db.Column(
        "template_override_id",
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Input identity
    input_index: int = db.Column(db.Integer, nullable=False)
    # Override required
    input_required: bool = db.Column(db.Boolean, nullable=False)
    # Owner (user) ID of the account
    owner_id: str = db.Column(
        db.String, db.ForeignKey("template.template_id"), nullable=False
    )


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
    # mulsig name
    multisig_name: str = db.Column(db.String(254), nullable=False)

    # Status of construct
    status: int = db.Column(db.Enum(MultiSigStatus), nullable=False)
    # The active_address is derived
    active_address: str = db.Column(db.String(66), nullable=True)
    # Threshold for signing
    threshold: int = db.Column(db.Integer, nullable=False)
    # Contains one or more members
    multisig_members = db.relationship(
        "MultiSigMember",
        backref="multi_signature",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )


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
    # ID of the MultiSig
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

    # Set active-address when either are not requestor
    explicit_sender: str = db.Column(db.String(66), nullable=True)
    explicit_sponsor: str = db.Column(db.String(66), nullable=True)

    # This is the tx_byte base64 string that requires signing
    tx_bytes: str = db.Column(db.String(200000), nullable=False)
    # Status
    status: int = db.Column(db.Enum(SignatureStatus), nullable=False)
    # Execution results
    transaction_passed: bool = db.Column(db.Boolean, nullable=True)
    transaction_response: str = db.Column(db.String(10240), nullable=True)


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
