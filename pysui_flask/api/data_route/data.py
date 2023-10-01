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

"""Route module."""
import base64
import json
from typing import Any, Union

# from http import HTTPStatus
from flask import Blueprint, request, current_app
from pysui_flask import db

from . import data_api
from pysui_flask.api_error import ErrorCodes, APIError


# Generic Sui


def _data_enabled():
    """Test for enablement or throw error."""
    if current_app.config[""] == 0:
        raise APIError("Data reading not enabled", ErrorCodes.PYSUI_ERROR_BASE)


@data_api.get("/gas/<string:address>")
def get_gas(address):
    """."""
    _data_enabled()


@data_api.get("/objects/<string:address>")
def get_objects(address):
    """."""
    _data_enabled()


@data_api.get("/account/<string:address>")
def get_account_for(address):
    """."""
    _data_enabled()


@data_api.get("/accounts")
def get_accounts():
    """."""
    _data_enabled()
