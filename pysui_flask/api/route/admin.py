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
from http import HTTPStatus
from flask import Blueprint, session, redirect, render_template, request, flash
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
        return "Hello Boss!"


@admin_api.route("/login", methods=["POST"])
def do_admin_log():
    """Verify admin login."""
    if request.form["password"] == os.getenv("ADMIN_KEY") and request.form[
        "username"
    ] == os.getenv("ADMIN_NAME"):
        session["admin_logged_in"] = True
    else:
        flash("wrong password!")
    return admin()