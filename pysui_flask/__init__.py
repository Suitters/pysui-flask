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

"""pysui-flask init."""

from flask_sqlalchemy import SQLAlchemy


# Global instance of db
db = SQLAlchemy()

# Database tables and relationships
# Registration
# Users
# Configurations

# class students(db.Model):
#     """."""

#     id = db.Column("student_id", db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     city = db.Column(db.String(50))
#     addr = db.Column(db.String(200))
#     pin = db.Column(db.String(10))

#     def __init__(self, name, city, addr, pin):
#         """."""
#         self.name = name
#         self.city = city
#         self.addr = addr
#         self.pin = pin
