# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from marshmallow import Schema, fields, post_load
from marshmallow.validate import OneOf, Length
from marshmallow_oneofschema import OneOfSchema

from flowmachine.features import AggregateNetworkObjects
from .base_exposed_query import BaseExposedQuery
from .total_network_objects import TotalNetworkObjectsSchema, TotalNetworkObjectsExposed
from .custom_fields import AggregationUnit, Statistic, Period

__all__ = ["AggregateNetworkObjectsSchema", "AggregateNetworkObjectsExposed"]


class InputToAggregateNetworkObjectsSchema(OneOfSchema):
    type_field = "query_kind"
    type_schemas = {"total_network_objects": TotalNetworkObjectsSchema}


class AggregateNetworkObjectsSchema(Schema):

    total_network_objects = fields.Nested(
        InputToAggregateNetworkObjectsSchema, required=True
    )
    statistic = Statistic()
    period = Period()

    @post_load
    def make_query_object(self, params):
        return AggregateNetworkObjectsExposed(**params)


class AggregateNetworkObjectsExposed(BaseExposedQuery):
    def __init__(self, *, total_network_objects, statistic, period):
        # Note: all input parameters need to be defined as attributes on `self`
        # so that marshmallow can serialise the object correctly.
        self.total_network_objects = total_network_objects
        self.statistic = statistic
        self.period = period

        if "period" not in self.total_network_objects:
            self.total_network_objects["period"] = self.period

    @property
    def _flowmachine_query_obj(self):
        """
        Return the underlying flowmachine aggregate_network_objects object.

        Returns
        -------
        Query
        """
        tot_network_objs = self.total_network_objects._flowmachine_query_obj

        return AggregateNetworkObjects(
            total_network_objects=tot_network_objs,
            statistic=self.statistic,
            period=self.period,
        )
