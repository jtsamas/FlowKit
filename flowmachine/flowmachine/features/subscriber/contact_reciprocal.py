# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-
"""
Classes for searching and dealing with reciprocal contacts.
"""

from ...utils.utils import parse_tables_ensuring_columns
from ..utilities import EventsTablesUnion
from .metaclasses import SubscriberFeature
from ...core.mixins.graph_mixin import GraphMixin
from .contact_balance import ContactBalance


class ContactReciprocal(GraphMixin, SubscriberFeature):
    """
    This class classifies a subscribers contact as reciprocal or not based. In
    addition to that, it calculates the number of incoming and outgoing events
    between the subscriber and her/his counterpart as well as the proportion
    that those events represent in total incoming and outgoing events.

    A reciprocal contact is a contact who has initiated contact and who also
    has been the counterpart of an initatiated contact by the subscriber.

    Parameters
    ----------
    start, stop : str
         iso-format start and stop datetimes
    hours : 2-tuple of floats, default 'all'
        Restrict the analysis to only a certain set
        of hours within each day.
    subscriber_subset : str, list, flowmachine.core.Query, flowmachine.core.Table, default None
        If provided, string or list of string which are msisdn or imeis to limit
        results to; or, a query or table which has a column with a name matching
        subscriber_identifier (typically, msisdn), to limit results to.
    exclude_self_calls : bool, default True
        Set to false to *include* calls a subscriber made to themself
    tables : str or list of strings, default 'all'
        Can be a string of a single table (with the schema)
        or a list of these. The keyword all is to select all
        subscriber tables

    Example
    -------

    >> s = ContactReciprocal('2016-01-01', '2016-01-08')
    >> s.get_dataframe()


              subscriber  msisdn_counterpart  events_in  events_out  proportion_in  \
        oQOm1YkDxljp3AVL    1jwYL3Nl1Y46lNeQ          0          21            0.0
        E9nlO1dMyVAWr60X    KXVqP6JyVDGzQa3b         17           0            1.0
        alye4Z3yz5ENvnXY    jWlyLwbGdvKV35Mm          0          19            0.0
        dXogRAnyg1Q9lE3J    qj8gk6qbN8R3DBdO          0          27            0.0
        5jLW0EWeoyg6NQo3    W8eEBvV6P8Jv01XZ         20           0            1.0
                     ...                 ...        ...         ...            ...

        proportion_out  reciprocal
                  1.0       False
                  0.0       False
                  1.0       False
                  1.0       False
                  0.0       False
                  ...         ...
    """

    def __init__(
        self,
        start,
        stop,
        *,
        hours="all",
        tables="all",
        exclude_self_calls=True,
        subscriber_subset=None,
    ):
        self.tables = tables
        self.start = start
        self.stop = stop
        self.hours = hours
        self.exclude_self_calls = exclude_self_calls

        column_list = ["msisdn", "msisdn_counterpart", "outgoing"]
        self.tables = parse_tables_ensuring_columns(
            self.connection, tables, column_list
        )

        self.contact_in_query = ContactBalance(
            self.start,
            self.stop,
            hours=self.hours,
            tables=self.tables,
            subscriber_identifier="msisdn",
            direction="in",
            exclude_self_calls=self.exclude_self_calls,
            subscriber_subset=subscriber_subset,
        )

        self.contact_out_query = ContactBalance(
            self.start,
            self.stop,
            hours=self.hours,
            tables=self.tables,
            subscriber_identifier="msisdn",
            direction="out",
            exclude_self_calls=self.exclude_self_calls,
            subscriber_subset=subscriber_subset,
        )

        super().__init__()

    def _make_query(self):

        sql = f"""
        SELECT
            COALESCE(I.subscriber, O.subscriber) AS subscriber,
            COALESCE(I.msisdn_counterpart, O.msisdn_counterpart) AS msisdn_counterpart,
            COALESCE(I.events_in, 0) AS events_in ,
            COALESCE(O.events_out, 0) AS events_out,
            COALESCE(I.proportion_in, 0) AS proportion_in,
            COALESCE(O.proportion_out, 0) AS proportion_out,
            CASE
                WHEN I.events_in IS NULL OR O.events_out IS NULL THEN FALSE
                ELSE TRUE
            END AS reciprocal
        FROM (
            SELECT
                subscriber,
                msisdn_counterpart,
                events AS events_in,
                proportion AS proportion_in
            FROM ({self.contact_in_query.get_query()}) C
        ) I
        FULL OUTER JOIN (
            SELECT
                subscriber,
                msisdn_counterpart,
                events AS events_out,
                proportion AS proportion_out
            FROM ({self.contact_out_query.get_query()}) C
        ) O
        ON
            I.subscriber = O.subscriber AND
            I.msisdn_counterpart = O.msisdn_counterpart
        """

        return sql


class ProportionContactReciprocal(SubscriberFeature):
    """
    This class calculates the proportion of reciprocal contacts a subscriber has.

    A reciprocal contact is a contact who has initiated contact and who also
    has been the counterpart of an initatiated contact by the subscriber.

    Parameters
    ----------
    start, stop : str
         iso-format start and stop datetimes
    hours : 2-tuple of floats, default 'all'
        Restrict the analysis to only a certain set
        of hours within each day.
    subscriber_subset : str, list, flowmachine.core.Query, flowmachine.core.Table, default None
        If provided, string or list of string which are msisdn or imeis to limit
        results to; or, a query or table which has a column with a name matching
        subscriber_identifier (typically, msisdn), to limit results to.
    exclude_self_calls : bool, default True
        Set to false to *include* calls a subscriber made to themself
    tables : str or list of strings, default 'all'
        Can be a string of a single table (with the schema)
        or a list of these. The keyword all is to select all
        subscriber tables

    Example
    -------

    >> s = ProportionContactReciprocal('2016-01-01', '2016-01-08')
    >> s.get_dataframe()

          subscriber  proportion
    9vXy462Ej8V1kpWl         0.0
    Q4mwVxpBOo7X2lb9         0.0
    5jLW0EWeoyg6NQo3         0.0
    QEoRM9vlkV18N4ZY         0.0
    a76Ajyb9dmEYNd8L         0.0
                 ...         ...
    """

    def __init__(
        self,
        start,
        stop,
        *,
        hours="all",
        tables="all",
        exclude_self_calls=True,
        subscriber_subset=None,
    ):
        self.start = start
        self.stop = stop
        self.hours = hours
        self.exclude_self_calls = exclude_self_calls
        self.tables = tables

        self.contact_reciprocal_query = ContactReciprocal(
            self.start,
            self.stop,
            hours=self.hours,
            tables=self.tables,
            exclude_self_calls=self.exclude_self_calls,
            subscriber_subset=subscriber_subset,
        )

    def _make_query(self):

        return f"""
        SELECT subscriber, AVG(reciprocal::int) AS proportion
        FROM  ({self.contact_reciprocal_query.get_query()}) R
        GROUP BY subscriber
        """


class ProportionEventReciprocal(SubscriberFeature):
    """
    This class calculates the proportion of events with a reciprocal contact
    per subscriber.  It is possible to fine-tune the period for which a
    reciprocal contact must have happened.

    A reciprocal contact is a contact who has initiated contact and who also
    has been the counterpart of an initatiated contact by the subscriber.

    Parameters
    ----------
    start, stop : str
         iso-format start and stop datetimes
    hours : 2-tuple of floats, default 'all'
        Restrict the analysis to only a certain set
        of hours within each day.
    contact_reciprocal: ContactReciprocal, default None
        An instance of ContactReciprocal listing which contacts are reciprocal
        and which are not. If none is passed, the class instantiates a list of
        reciprocal contacts with the same parameters as the ones used to
        retrieve the requested events for consideration.
    subscriber_identifier : {'msisdn', 'imei'}, default 'msisdn'
        Either msisdn, or imei, the column that identifies the subscriber.
    subscriber_subset : str, list, flowmachine.core.Query, flowmachine.core.Table, default None
        If provided, string or list of string which are msisdn or imeis to limit
        results to; or, a query or table which has a column with a name matching
        subscriber_identifier (typically, msisdn), to limit results to.
    direction : {'in', 'out', 'both'}, default 'out'
        Whether to consider calls made, received, or both. Defaults to 'out'.
    exclude_self_calls : bool, default True
        Set to false to *include* calls a subscriber made to themself
    tables : str or list of strings, default 'all'
        Can be a string of a single table (with the schema)
        or a list of these. The keyword all is to select all
        subscriber tables

    Example
    -------

    >> s = ProportionEventReciprocal('2016-01-01', '2016-01-08')
    >> s.get_dataframe()

          subscriber  proportion
    9vXy462Ej8V1kpWl         0.0
    Q4mwVxpBOo7X2lb9         0.0
    5jLW0EWeoyg6NQo3         0.0
    QEoRM9vlkV18N4ZY         0.0
    a76Ajyb9dmEYNd8L         0.0
                 ...         ...
    """

    def __init__(
        self,
        start,
        stop,
        contact_reciprocal=None,
        *,
        direction="both",
        subscriber_identifier="msisdn",
        hours="all",
        subscriber_subset=None,
        tables="all",
        exclude_self_calls=True,
    ):

        self.start = start
        self.stop = stop
        self.subscriber_identifier = subscriber_identifier
        self.hours = hours
        self.exclude_self_calls = exclude_self_calls
        self.direction = direction

        if self.direction == "both":
            column_list = [self.subscriber_identifier, "msisdn", "msisdn_counterpart"]
        else:
            column_list = [
                self.subscriber_identifier,
                "msisdn",
                "msisdn_counterpart",
                "outgoing",
            ]

        self.tables = parse_tables_ensuring_columns(
            self.connection, tables, column_list
        )

        self.unioned_query = EventsTablesUnion(
            self.start,
            self.stop,
            tables=self.tables,
            columns=column_list,
            hours=hours,
            subscriber_identifier=subscriber_identifier,
            subscriber_subset=subscriber_subset,
        )

        if contact_reciprocal:
            self.contact_reciprocal_query = contact_reciprocal
        else:
            contact_start = start
            contact_stop = stop
            contact_hours = hours
            contact_tables = self.tables
            self.contact_reciprocal_query = ContactReciprocal(
                contact_start,
                contact_stop,
                tables=contact_tables,
                hours=contact_hours,
                exclude_self_calls=self.exclude_self_calls,
                subscriber_subset=subscriber_subset,
            )

        super().__init__()

    def _make_query(self):

        filters = []
        if self.direction != "both":
            filters.append(
                f"outgoing IS {'TRUE' if self.direction == 'out' else 'FALSE'}"
            )
        if self.exclude_self_calls:
            filters.append("subscriber != msisdn_counterpart")
        where_clause = f"WHERE {' AND '.join(filters)} " if len(filters) > 0 else ""

        on_clause = f"""
        ON {'U.subscriber' if self.subscriber_identifier == 'msisdn' else 'U.msisdn'} = R.subscriber
        AND  U.msisdn_counterpart = R.msisdn_counterpart
        """

        sql = f"""
        SELECT subscriber, AVG(reciprocal::int) AS proportion
        FROM (
            SELECT U.subscriber, COALESCE(reciprocal, FALSE) AS reciprocal
            FROM (
                SELECT *
                FROM ({self.unioned_query.get_query()}) U
                {where_clause}
            ) U
            LEFT JOIN (
                SELECT subscriber, msisdn_counterpart, reciprocal
                FROM ({self.contact_reciprocal_query.get_query()}) R
            ) R
            {on_clause}
        ) R
        GROUP BY subscriber
        """

        return sql
