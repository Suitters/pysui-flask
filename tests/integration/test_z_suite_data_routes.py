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

"""Pytest data routes."""

import base64
import json
import pytest


from flask.testing import FlaskClient


def test_data_gas(client: FlaskClient, accounts: dict):
    """Get gas for account."""
    users = accounts["users"]
    response = client.get(
        "/data/" + users[0]["active_address"] + "/gas", json={}
    )
    assert response.status_code == 200
    result = response.json
    print(result)


def test_data_objects(client: FlaskClient, accounts: dict):
    """Get objects for account."""
    users = accounts["users"]
    response = client.get(
        "/data/" + users[0]["active_address"] + "/objects", json={}
    )
    assert response.status_code == 200
    result = response.json
    print(result)

def test_data_object(client: FlaskClient):
    """Get objects for account."""
    response = client.get(
        "/data/object/0x322ade55a618a642dbb14f345404313174b95cabf4d542eec554c52022aba562", json={}
    )
    assert response.status_code == 200
    result = response.json
    print(result)
