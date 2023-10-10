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

"""Flask config."""

import os
from pathlib import Path
from datetime import timedelta
from dataclasses import dataclass
from dotenv import load_dotenv

# This gets the app dir and we want to go one back
basedir = Path(os.path.abspath(os.path.dirname(__file__)))
load_dotenv(basedir.joinpath(".env"))


@dataclass
class Constraints:
    """Constraints for routes."""

    entries_per_page: int = 50
    allow_pwd_change_attempts:int = int(os.environ.get("ALLOW_PWD_CHANGE_ATTEMPTS"))
    allow_anonymous_dataread:bool = bool(os.environ.get("ALLOW_ANONYMOUS_DATA_READ"))

class Config:
    """Base config defaults."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    SESSION_TYPE = os.environ.get("SESSION_TYPE")
    SESSION_PERMANENT = os.environ.get("SESSION_PERMANENT")
    RPC_URL = os.environ.get("RPC_URL")
    CONSTRAINTS = Constraints()


class ProdConfig(Config):
    """."""

    FLASK_ENV = "production"
    ADMIN_NAME = os.environ.get("PROD_ADMIN_NAME")
    ADMIN_PASSWORD = os.environ.get("PROD_ADMIN_PASSWORD")
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("PROD_DATABASE")
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_FILE_THRESHOLD = int(os.environ.get("PROD_SESSION_FILE_THRESHOLD"))
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=(int(os.environ.get("PROD_PERMANENT_SESSION_LIFETIME")))
    )


class DevConfig(Config):
    """."""

    FLASK_ENV = "development"
    ADMIN_NAME = os.environ.get("DEV_ADMIN_NAME")
    ADMIN_PASSWORD = os.environ.get("DEV_ADMIN_PASSWORD")
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE")
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_FILE_THRESHOLD = int(os.environ.get("DEV_SESSION_FILE_THRESHOLD"))
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=(int(os.environ.get("DEV_PERMANENT_SESSION_LIFETIME")))
    )


def load_config() -> Config:
    """."""
    cfg = os.environ.get("USE_CONFIG")
    if cfg == "Dev":
        return DevConfig()
    elif cfg == "Prod":
        return ProdConfig()
    else:
        raise ValueError(f"{cfg} not a known config. Use 'Dev' or 'Prod'")
