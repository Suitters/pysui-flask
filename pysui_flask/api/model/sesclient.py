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

"""Session client configuration."""

from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin


@dataclass
class _BaseConfig(DataClassJsonMixin):
    """Base configuration dataclass.

    At a minimum requires a rpc_url
    ws_url is based on source of configuration. Admin will pop from default configuration
    """

    rpc_url: str
    default_address: str = field(default_factory=str)
    ws_url: str = field(default_factory=str)
    key: str = field(default_factory=str)


@dataclass
class UserConfig(_BaseConfig):
    """User configuration dataclass.

    May be updated if settings change
    """


@dataclass
class AdminConfig(_BaseConfig):
    """Admin configuration dataclass.

    Derived from default_config on SuiConfig
    """

    addresses: list[str] = field(default_factory=list)
    additional_keys: list[str] = field(default_factory=list)


if __name__ == "__main__":
    pass
