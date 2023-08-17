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

    id = db.Column("user_id", db.Integer, nullable=False, primary_key=True)
    # Auto generated... this is not the private key of account
    user_key = db.Column(db.String(44), nullable=False)
    # One way hashed value from password text
    password = db.Column(db.String(64), nullable=False)
    # user email or string, must be unique clear
    email = db.Column(db.String(254), nullable=False)
    # Encode a role
    user_role = db.Column(db.Enum(UserRole), nullable=False)
    # When registered
    applicationdate = db.Column(db.DateTime)


class UserConfiguration(db.Model):
    """Configuration for instantiating SuiConfig for User."""

    id = db.Column(
        "configuration_id", db.Integer, nullable=False, primary_key=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    user = db.relationship("User", backref="user", uselist=False)
    rpc_url = db.Column(db.String(254), nullable=False)
    ws_url = db.Column(db.String(254), nullable=True)
    active_address = db.Column(db.String(44), nullable=False)
    account_key = db.Column(db.String(44), nullable=False)
    config_keys = db.relationship("ConfigKeys", backref="user_configuration")


class ConfigKeys(db.Model):
    """."""

    id = db.Column("key_id", db.Integer, nullable=False, primary_key=True)
    key_pair = db.Column(db.String(44), nullable=False)
    config_id = db.Column(
        db.Integer, db.ForeignKey("user_configuration.configuration_id")
    )
