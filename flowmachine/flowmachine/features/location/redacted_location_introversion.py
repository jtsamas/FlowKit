# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-


from flowmachine.features import LocationIntroversion
from flowmachine.features.location.redacted_location_metric import (
    RedactedLocationMetric,
)


from ...core import Query
from ...core.mixins import GeoDataMixin


class RedactedLocationIntroversion(RedactedLocationMetric, GeoDataMixin, Query):
    """
    Calculates the proportions of events that take place
    within a location in which all involved parties
    are located in the same location (introversion), where there are more than 15
    subscribers in that location.

    Parameters
    ----------
    location_introversion : LocationIntroversion
        LocationIntroversion query to redact
    """

    def __init__(self, *, location_introversion: LocationIntroversion):
        self.redaction_target = location_introversion
        self.spatial_unit = location_introversion.spatial_unit

        super().__init__()

    def _make_query(self):
        location_columns = self.spatial_unit.location_id_columns

        if self.redaction_target.direction == "both":
            sql_direction = ""
        elif self.redaction_target.direction == "in":
            sql_direction = """
                WHERE NOT A.outgoing
            """
        elif self.redaction_target.direction == "out":
            sql_direction = """
                WHERE A.outgoing
            """

        sql = f"""
        WITH unioned_table AS ({self.redaction_target.unioned_query.get_query()})
        SELECT {', '.join(location_columns)}, sum(introverted::integer)/count(*)::float as value FROM (
            SELECT
               {', '.join(f'A.{c} as {c}' for c in location_columns)},
               {' AND '.join(f'A.{c} = B.{c}' for c in location_columns)} as introverted,
               A.subscriber
            FROM unioned_table as A
            INNER JOIN unioned_table AS B
                  ON A.id = B.id
                     AND A.outgoing != B.outgoing
                     {sql_direction}
        ) _
        GROUP BY {', '.join(location_columns)}
        HAVING count(distinct subscriber) > 15
        ORDER BY {', '.join(location_columns)} DESC
        """

        return sql
