# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-
"""
Calculates various entropy metrics for subscribers with a specified time
period.
"""

from abc import ABCMeta
from .metaclasses import SubscriberFeature
from .contact_balance import ContactBalance
from ..utilities.sets import EventsTablesUnion
from ..utilities.subscriber_locations import subscriber_locations
from ...utils.utils import get_columns_for_level
from ...core import Table


class BaseEntropy(SubscriberFeature, metaclass=ABCMeta):
    """ Base query for calculating entropy of subscriber features. """

    def _make_query(self):

        return f"""
        SELECT
            subscriber,
            -1 * SUM( relative_freq * LN( relative_freq ) ) AS entropy
        FROM ({self._relative_freq_query}) u
        GROUP BY subscriber
        """

    @property
    def _absolute_freq_query(self):

        raise NotImplementedError

    @property
    def _relative_freq_query(self):
        return f"""
        SELECT
            subscriber,
            absolute_freq::float / ( SUM( absolute_freq ) OVER ( PARTITION BY subscriber ) ) AS relative_freq
        FROM ({self._absolute_freq_query}) u
        """


class PeriodicEntropy(BaseEntropy):
    """
    Calculates the recurrence period entropy for events, that is the entropy
    associated with the period in which events take place. For instance, if
    events regularly occur at a certain time of day, say at 9:00 and 18:00 then
    this user will have a low period entropy.

    Parameters
    ----------
    start, stop : str
         iso-format start and stop datetimes
    phase : {"century", "day", "decade", "dow", "doy", "epoch", "hour",
            "isodow", "isoyear", "microseconds", "millennium", "milliseconds",
            "minute", "month", "quarter", "second", "timezone", "timezone_hour",
            "timezone_minute", "week", "year"}, default 'hour'
        The phase of recurrence for which one wishes to calculate the entropy.
    subscriber_identifier : {'msisdn', 'imei'}, default 'msisdn'
        Either msisdn, or imei, the column that identifies the subscriber.
    subscriber_subset : str, list, flowmachine.core.Query, flowmachine.core.Table, default None
        If provided, string or list of string which are msisdn or imeis to limit
        results to; or, a query or table which has a column with a name matching
        subscriber_identifier (typically, msisdn), to limit results to.
    direction : {'in', 'out', 'both'}, default 'out'
        Whether to consider calls made, received, or both. Defaults to 'out'.
    hours : 2-tuple of floats, default 'all'
        Restrict the analysis to only a certain set
        of hours within each day.
    tables : str or list of strings, default 'all'
        Can be a string of a single table (with the schema)
        or a list of these. The keyword all is to select all
        subscriber tables

    Examples
    --------

    >>> s = PeriodicEntropy("2016-01-01", "2016-01-07")
    >>> s.get_dataframe()

             subscriber   entropy
       038OVABN11Ak4W5P  2.805374
       09NrjaNNvDanD8pk  2.730881
       0ayZGYEQrqYlKw6g  2.802434
       0DB8zw67E9mZAPK2  2.476354
       0Gl95NRLjW2aw8pW  2.788854
                    ...       ...
    """
    def __init__(
        self,
        start,
        stop,
        phase="hour",
        *,
        subscriber_identifier="msisdn",
        direction="both",
        hours="all",
        subscriber_subset=None,
        tables="all",
    ):

        self.start = start
        self.stop = stop
        self.subscriber_identifier = subscriber_identifier
        self.direction = direction
        self.hours = hours

        if direction not in {"in", "out", "both"}:
            raise ValueError("{} is not a valid direction.".format(self.direction))

        if self.direction == "both":
            column_list = [self.subscriber_identifier, "datetime"]
            self.tables = tables
        else:
            column_list = [self.subscriber_identifier, "datetime", "outgoing"]
            self.tables = self._parse_tables_ensuring_direction_present(tables)

        # extracted from the POSTGRES manual
        allowed_phases = (
            "century",
            "day",
            "decade",
            "dow",
            "doy",
            "epoch",
            "hour",
            "isodow",
            "isoyear",
            "microseconds",
            "millennium",
            "milliseconds",
            "minute",
            "month",
            "quarter",
            "second",
            "timezone",
            "timezone_hour",
            "timezone_minute",
            "week",
            "year",
        )

        if phase not in allowed_phases:
            raise ValueError(
                f"{phase} is not a valid phase. Choose one of {allowed_phases}"
            )

        self.phase = phase

        self.unioned_query = EventsTablesUnion(
            self.start,
            self.stop,
            tables=self.tables,
            columns=column_list,
            hours=hours,
            subscriber_identifier=subscriber_identifier,
            subscriber_subset=subscriber_subset,
        )
        super().__init__()

    def _parse_tables_ensuring_direction_present(self, tables):

        if isinstance(tables, str) and tables.lower() == "all":
            tables = [f"events.{t}" for t in self.connection.subscriber_tables]
        elif type(tables) is str:
            tables = [tables]
        else:
            tables = tables

        parsed_tables = []
        tables_lacking_direction_column = []
        for t in tables:
            if "outgoing" in Table(t).column_names:
                parsed_tables.append(t)
            else:
                tables_lacking_direction_column.append(t)

        if tables_lacking_direction_column:
            raise MissingDirectionColumnError(tables_lacking_direction_column)

        return parsed_tables

    @property
    def _absolute_freq_query(self):

        where_clause = ""
        if self.direction != "both":
            where_clause = (
                f"WHERE outgoing IS {'TRUE' if self.direction == 'out' else 'FALSE'}"
            )

        return f"""
        SELECT subscriber, COUNT(*) AS absolute_freq FROM
        ({self.unioned_query.get_query()}) u
        {where_clause}
        GROUP BY subscriber, EXTRACT( {self.phase} FROM datetime )
        HAVING COUNT(*) > 0
        """


class LocationEntropy(BaseEntropy):
    """
    Calculates the entropy of locations visited. For instance, if an individual
    regularly makes her/his calls from certain location then this user will
    have a low location entropy.

    Parameters
    ----------
    start, stop : str
         iso-format start and stop datetimes
    level : str, default 'cell'
        Levels can be one of:
            'cell':
                The identifier as it is found in the CDR itself
            'versioned-cell':
                The identifier as found in the CDR combined with the version from
                the cells table.
            'versioned-site':
                The ID found in the sites table, coupled with the version
                number.
            'polygon':
                A custom set of polygons that live in the database. In which
                case you can pass the parameters column_name, which is the column
                you want to return after the join, and table_name, the table where
                the polygons reside (with the schema), and additionally geom_col
                which is the column with the geometry information (will default to
                'geom')
            'admin*':
                An admin region of interest, such as admin3. Must live in the
                database in the standard location.
            'grid':
                A square in a regular grid, in addition pass size to
                determine the size of the polygon.
    subscriber_identifier : {'msisdn', 'imei'}, default 'msisdn'
        Either msisdn, or imei, the column that identifies the subscriber.
    subscriber_subset : str, list, flowmachine.core.Query, flowmachine.core.Table, default None
        If provided, string or list of string which are msisdn or imeis to limit
        results to; or, a query or table which has a column with a name matching
        subscriber_identifier (typically, msisdn), to limit results to.
    hours : 2-tuple of floats, default 'all'
        Restrict the analysis to only a certain set
        of hours within each day.
    tables : str or list of strings, default 'all'
        Can be a string of a single table (with the schema)
        or a list of these. The keyword all is to select all
        subscriber tables

    Examples
    --------

    >>> s = LocationEntropy("2016-01-01", "2016-01-07")
    >>> s.get_dataframe()

              subscriber   entropy
        038OVABN11Ak4W5P  2.832747
        09NrjaNNvDanD8pk  3.184784
        0ayZGYEQrqYlKw6g  3.072458
        0DB8zw67E9mZAPK2  2.838989
        0Gl95NRLjW2aw8pW  2.997069
                     ...       ...
    """
    def __init__(
        self,
        start,
        stop,
        *,
        level="cell",
        column_name=None,
        subscriber_identifier="msisdn",
        hours="all",
        subscriber_subset=None,
        tables="all",
        ignore_nulls=True,
    ):

        self.subscriber_locations = subscriber_locations(
            start=start,
            stop=stop,
            level=level,
            column_name=column_name,
            table=tables,
            hours=hours,
            subscriber_identifier=subscriber_identifier,
            subscriber_subset=subscriber_subset,
            ignore_nulls=ignore_nulls,
        )
        self.location_cols = ", ".join(
            get_columns_for_level(level=level, column_name=column_name)
        )
        super().__init__()

    @property
    def _absolute_freq_query(self):

        return f"""
        SELECT subscriber, COUNT(*) AS absolute_freq FROM
        ({self.subscriber_locations.get_query()}) u
        GROUP BY subscriber, {self.location_cols}
        HAVING COUNT(*) > 0
        """


class ContactEntropy(BaseEntropy):
    """
    Calculates the entropy of locations visited. For instance, if an individual
    regularly interact with a few determined contacts then this user will have
    a low contact entropy.

    Parameters
    ----------
    start, stop : str
         iso-format start and stop datetimes
    subscriber_identifier : {'msisdn', 'imei'}, default 'msisdn'
        Either msisdn, or imei, the column that identifies the subscriber.
    subscriber_subset : str, list, flowmachine.core.Query, flowmachine.core.Table, default None
        If provided, string or list of string which are msisdn or imeis to limit
        results to; or, a query or table which has a column with a name matching
        subscriber_identifier (typically, msisdn), to limit results to.
    direction : {'in', 'out', 'both'}, default 'out'
        Whether to consider calls made, received, or both. Defaults to 'out'.
    hours : 2-tuple of floats, default 'all'
        Restrict the analysis to only a certain set
        of hours within each day.
    tables : str or list of strings, default 'all'
        Can be a string of a single table (with the schema)
        or a list of these. The keyword all is to select all
        subscriber tables
    exclude_self_calls : bool, default True
        Set to false to *include* calls a subscriber made to themself

    Examples
    --------

    >>> s = ContactEntropy("2016-01-01", "2016-01-07")
    >>> s.get_dataframe()

          subscriber   entropy
    2ZdMowMXoyMByY07  0.692461
    MobnrVMDK24wPRzB  0.691761
    0Ze1l70j0LNgyY4w  0.693147
    Nnlqka1oevEMvVrm  0.607693
    gPZ7jbqlnAXR3JG5  0.686211
                 ...       ...
    """
    def __init__(
        self,
        start,
        stop,
        *,
        subscriber_identifier="msisdn",
        direction="both",
        hours="all",
        subscriber_subset=None,
        tables="all",
        exclude_self_calls=True,
    ):

        self.contact_balance = ContactBalance(
            start=start,
            stop=stop,
            hours=hours,
            tables=tables,
            subscriber_identifier=subscriber_identifier,
            direction=direction,
            exclude_self_calls=exclude_self_calls,
            subscriber_subset=subscriber_subset,
        )

    @property
    def _absolute_freq_query(self):

        return f"""
        SELECT subscriber, events AS absolute_freq FROM
        ({self.contact_balance.get_query()}) u
        """

    @property
    def _relative_freq_query(self):

        return f"""
        SELECT subscriber, proportion AS relative_freq FROM
        ({self.contact_balance.get_query()}) u
        """
