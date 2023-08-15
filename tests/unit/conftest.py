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

"""Pytest fixtures (setup/teardown) module."""

from pathlib import Path
import pytest

from flask.testing import FlaskClient
from pysui_flask import app as pysui_app


def _session_cleanup():
    """Deletes the session directory after all tests in module completed."""
    cwd = Path.cwd().joinpath("flask_session")
    if cwd.exists() and cwd.is_dir():
        for pfile in cwd.glob("*"):
            if pfile.is_file():
                pfile.unlink()
        cwd.rmdir()


@pytest.fixture(scope="module")
def client() -> FlaskClient:
    """."""
    app = pysui_app.create_app()
    app.config["TESTING"] = True

    with app.app_context():
        with app.test_client() as client:
            yield client
            print("exiting client")
    print("exiting context")
    _session_cleanup()
