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
    redirect,
    render_template,
    request,
    Response,
    flash,
    session,
    after_this_request,
)
from flasgger import swag_from

admin_api = Blueprint("admin", __name__)


@admin_api.route("/")
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
        return render_template("admin_login.html")
    else:
        print(f"CFG: {session.get('client_cfg')}")
        return f"Hello {session.get('name')}, you are logged in"


@admin_api.route("/login", methods=["POST"])
def do_admin_log():
    """Verify admin login."""
    in_data = None
    content_type = request.headers.get("Content-Type")
    if content_type == "application/json":
        in_data = json.loads(request.get_json())
    elif (
        content_type == "multipart/form-data"
        or content_type == "application/x-www-form-urlencoded"
    ):
        in_data = request.form.to_dict()

    if (
        in_data["username"] == os.environ["ADMIN_NAME"]
        and in_data["password"] == os.environ["ADMIN_KEY"]
    ):
        session["name"] = in_data["username"]
        session["admin_logged_in"] = True
        session["client_cfg"] = {"1": "foo", "2": "bar", "3": {"a": 4}}
        return {"session": session.sid}
    return admin()
