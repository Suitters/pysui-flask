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

import json
from http import HTTPStatus
from flask import (
    Blueprint,
    session,
    request,
)
from flasgger import swag_from
from . import UserRole, verify_credentials


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
    """Admin login with credential check."""
    in_data = json.loads(request.get_json())
    # Get the User object of the admin role
    # Throws exception
    user = verify_credentials(
        user_name=in_data["username"],
        user_password=in_data["password"],
        expected_role=UserRole.admin,
    )
    session["name"] = in_data["username"]
    session["admin_logged_in"] = True
    return {"session": session.sid}


# Add user
