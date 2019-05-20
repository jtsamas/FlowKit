# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-
"""
Define a DB model for storing the process of ingestion
"""

import pendulum
from pendulum.date import Date as pendulumDate

from sqlalchemy import Column, String, DateTime, Date, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session

from etl.etl_utils import CDRType, State

Base = declarative_base()

# pylint: disable=too-few-public-methods
class ETLRecord(Base):
    """
    DB Model for storing the process of ingestion
    for found files.
    """

    __tablename__ = "etl_records"
    __table_args__ = {"schema": "etl"}

    id = Column(Integer, primary_key=True)
    cdr_type = Column(String)
    cdr_date = Column(Date)
    state = Column(String)
    timestamp = Column(DateTime)

    def __init__(self, *, cdr_type: str, cdr_date: pendulumDate, state: str):

        self.cdr_type = CDRType(cdr_type)
        self.cdr_date = cdr_date
        self.state = State(state)
        self.timestamp = pendulum.utcnow()

    @classmethod
    def set_state(
        cls, *, cdr_type: str, cdr_date: pendulumDate, state: str, session: Session
    ) -> None:
        """
        Add new row to the etl book-keeping table.

        Parameters
        ----------
        cdr_type : str
            CDR type of file being processed ("calls", "sms", "mds" or "topups")
        cdr_date : Date
            The date with which the file's data is associated
        state : str
            The state in the ingestion process the file currently
            is ("ingest", "quarantine" or "archive")
        session : Session
            A sqlalchemy session for a DB in which this model exists.
        """
        row = cls(cdr_type=cdr_type, cdr_date=cdr_date, state=state)
        session.add(row)
        session.commit()