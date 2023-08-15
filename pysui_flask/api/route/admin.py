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

"""Administration module."""

import os
import json
from http import HTTPStatus
from flask import (
    Blueprint,
    session,
    request,
)
from flasgger import swag_from
from pysui_flask.api.model.sesclient import AdminConfig
from pysui import SuiConfig

admin_api = Blueprint("admin", __name__)


@admin_api.get("/")
@swag_from(
    {
        "responses": {
            HTTPStatus.OK.value: {
                "description": "Admin for pysui-flask",
            }
        }
    }
)
def admin():
    """Admin root.

    A more detailed description of the endpoint
    """
    if not session.get("admin_logged_in"):
        return {"error": "Admin session not found"}
    else:
        return {"session": session.sid}


@admin_api.get("/login")
def admin_login():
    """Verify admin login."""
    in_data = None

    if request.headers.get("Content-Type") == "application/json":
        in_data = json.loads(request.get_json())
    else:
        pass  # Error
    if (
        in_data["username"] == os.environ["ADMIN_NAME"]
        and in_data["password"] == os.environ["ADMIN_KEY"]
    ):
        session["name"] = in_data["username"]
        session["admin_logged_in"] = True

        session["client_cfg"] = AdminConfig.from_config(
            SuiConfig.default_config()
        ).to_json()
    return {"session": session.sid}


@admin_api.get("/accounts")
def admin_accounts():
    """Verify admin login."""
    if not session.get("admin_logged_in"):
        return {"error": "Admin session not found"}
    adm_cfg = AdminConfig.from_json(session["client_cfg"])
    all_addys: list[str] = [adm_cfg.active_address]
    all_addys.extend(adm_cfg.additional_addresses)
    return {"addresses": all_addys}
