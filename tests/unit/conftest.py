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
    session_dir = Path.cwd().joinpath("flask_session")
    if session_dir.exists() and session_dir.is_dir():
        for pfile in session_dir.glob("*"):
            if pfile.is_file():
                pfile.unlink()
        session_dir.rmdir()


def _db_cleanup():
    """Delete the test_project database after all tests in module completed."""
    instance_dir = Path.cwd().joinpath("instance")
    if instance_dir.exists() and instance_dir.is_dir():
        for pfile in instance_dir.glob("*"):
            if pfile.is_file():
                pfile.unlink()
        instance_dir.rmdir()


def cleanup_wipe():
    """Cleans up (wipes) session and test db."""
    _session_cleanup()
    _db_cleanup()


@pytest.fixture(scope="session")
def client() -> FlaskClient:
    """Initialize a Flask test client."""
    cleanup_wipe()
    app = pysui_app.create_app()
    app.config["TESTING"] = True

    with app.app_context():
        with app.test_client() as client:
            yield client
    cleanup_wipe()
