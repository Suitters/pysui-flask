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


class MultiSigStatus(enum.Enum):
    """Extend as needed."""

    pending_attestation = 1
    confirmed = 2
    rejected = 3


class MsMemberStatus(enum.Enum):
    """Extend as needed."""

    request_attestation = 1
    confirmed = 2
    rejected = 3


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
        "MultiSigRequests",
        backref="user",
        lazy=True,
        uselist=True,
        cascade="all, delete-orphan",
    )
    # May or may not have signing requests
    sign_requests = db.relationship(
        "SignatureRequests",
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
    # May be nullable if role of primary owner is MultiSig type
    # The active_address gets completed when a multisig is confirmed
    active_address: str = db.Column(db.String(66), nullable=True)
    private_key: str = db.Column(db.String(44), nullable=True)


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
class MultiSigRequests(db.Model):
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
    # This is the challenge phrase requiring signing
    attestation_phrase: str = db.Column(db.String(64), nullable=False)


@dataclasses.dataclass
class SignatureRequests(db.Model):
    """Signature requesst queue."""

    id: int = db.Column(
        "sig_request_id",
        db.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    signing_id: str = db.Column(
        db.String, db.ForeignKey("user.account_key"), nullable=False
    )
    # This is the digest that requires signing
