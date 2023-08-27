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


def _dir_cleanup(folder: str):
    """Cleanup folder and contents."""
    target_dir = Path.cwd().joinpath(folder)
    if target_dir.exists() and target_dir.is_dir():
        for pfile in target_dir.glob("*"):
            if pfile.is_file():
                pfile.unlink()
        target_dir.rmdir()


def wipe_clean():
    """Cleans up (wipes) session and test db."""
    _dir_cleanup("flask_session")
    _dir_cleanup("instance")


@pytest.fixture(scope="session")
def client() -> FlaskClient:
    """Initialize a Flask test client."""
    wipe_clean()
    app = pysui_app.create_app()
    app.config["TESTING"] = True

    with app.app_context():
        with app.test_client() as client:
            yield client
    wipe_clean()
