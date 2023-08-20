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

import enum
from . import db

from sqlalchemy import Enum


class UserRole(enum.Enum):
    """."""

    admin = 1
    user = 2


class User(db.Model):
    """User table contains indicative data and keys."""

    id = db.Column(
        "user_id",
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )
    # Auto generated... this is not the private key of account
    account_key = db.Column(db.String(44), nullable=False)
    # One way hashed value from password text
    password = db.Column(db.String(64), nullable=False)
    # user email or string, must be unique clear
    user_name_or_email = db.Column(db.String(254), nullable=False)
    # Encode a role
    user_role = db.Column(db.Enum(UserRole), nullable=False)
    # When registered
    applicationdate = db.Column(db.DateTime)
    # May or may not have a configuration
    configuration = db.relationship(
        "UserConfiguration",
        backref="user",
        lazy=True,
        uselist=False,
        cascade="all, delete-orphan",
    )


class UserConfiguration(db.Model):
    """Configuration for instantiating SuiConfig for User."""

    id = db.Column(
        "configuration_id", db.Integer, nullable=False, primary_key=True
    )
    # Owner (user) ID relationship
    owner_id = db.Column(
        db.String, db.ForeignKey("user.account_key"), nullable=False
    )
    # Urls
    rpc_url = db.Column(db.String(254), nullable=False)
    ws_url = db.Column(db.String(254), nullable=True)
    # Addresses and keys
    active_address = db.Column(db.String(66), nullable=False)
    private_key = db.Column(db.String(44), nullable=False)
