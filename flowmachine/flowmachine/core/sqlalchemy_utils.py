# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pandas as pd
from sqlalchemy import Table, MetaData
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import Selectable


def get_sqlalchemy_table_definition(fully_qualified_table_name, *, engine):
    """
    Return sqlalchemy Table object for table with the given name.

    Parameters
    ----------
    fully_qualified_table_name : str
        Fully qualified table name. Example: "events.calls"
    engine : sqlalchemy.engine.Engine
        SQLAlchemy engine to use for reading the table information.

    Returns
    -------
    sqlalchemy.Table
    """
    metadata = MetaData()
    if fully_qualified_table_name == "events.calls":
        schema = "events"
        table_name = "calls"
    elif fully_qualified_table_name == "events.sms":
        schema = "events"
        table_name = "sms"
    elif fully_qualified_table_name == "events.mds":
        schema = "events"
        table_name = "mds"
    elif fully_qualified_table_name == "events.topups":
        schema = "events"
        table_name = "topups"
    else:
        raise NotImplementedError(
            f"No sqlalchemy definition found for table: '{fully_qualified_table_name}'"
        )

    return Table(
        table_name, metadata, schema=schema, autoload=True, autoload_with=engine
    )


def get_sql_string(query):
    """
    Return SQL string compiled from the given sqlalchemy query (using the PostgreSQL dialect).

    Parameters
    ----------
    query : sqlalchemy.sql.Selectable
        SQLAlchemy query

    Returns
    -------
    str
        SQL string compiled from the sqlalchemy query.
    """
    assert isinstance(query, Selectable)
    compiled_query = query.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    )
    sql = str(compiled_query)
    return sql


def get_query_result_as_dataframe(query, *, engine):
    """
    Run the given sqlalchemy query and return the result as a pandas DataFrame.

    Parameters
    ----------
    query : sqlalchemy.sql.Selectable
        The SQLAlchemy query to run.
    engine : sqlalchemy.engine.Engine
        SQLAlchemy engine to use for reading the table information.

    Returns
    -------
    pandas.DataFrame
        Data frame containing the result.
    """
    assert isinstance(query, Selectable)

    with engine.connect() as con:
        result = con.execute(query)

    columns = [c.name for c in query.columns]
    df = pd.DataFrame(result.fetchall(), columns=columns)
    return df


def get_sqlalchemy_column(table, column_str):
    """
    Given a sqlalchemy table and a string with a column description, return
    the actual sqlalchemy Column object (or a sqlalchemy Label object if
    `column_str` contains an alias such as "<column> AS <alias>".

    Parameters
    ----------
    table : sqlalchemy.Table
        The table for which to obtain the column.
    column_str : str
        The column name, optionally describing an alias via

    Returns
    -------
    sqlalchemy.Column or sqlalchemy.sql.elements.Label

    Examples
    --------

        >>> get_sqlalchemy_column(table, "msisdn")
        >>> get_sqlalchemy_column(table, "msisdn AS subscriber")
    """
    assert isinstance(table, Table)
    parts = column_str.split()
    if len(parts) == 1:
        colname = parts[0]
        col = table.c[colname]
    elif len(parts) == 3:
        assert parts[1].lower() == "as"
        colname = parts[0]
        label = parts[2]
        col = table.c[colname].label(label)
    else:
        raise ValueError(f"Not a valid column expression: '{column_str}'")

    return col
