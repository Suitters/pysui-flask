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

"""Pytest admin and account multisig routes."""

import json
from flask.testing import FlaskClient


def test_add_multisig(client: FlaskClient):
    """Should be empty."""
    response = client.post("/admin/multisig_account", json=json.dumps({}))
    assert response.status_code == 200
    result = response.json
    assert result["result"]["stub_new_multisig_account"] == True
