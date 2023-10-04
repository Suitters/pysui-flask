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


@pytest.fixture(scope="module")
def accounts(client: FlaskClient):
    """."""
    response = client.get("/data/accounts", json={})
    assert response.status_code == 200
    result = response.json
    yield result["result"]["accounts"]


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
