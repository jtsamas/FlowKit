# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-
"""
Contains the definition of dummy callables to be used when testing
"""

import os
import structlog

from uuid import uuid1
from pendulum import utcnow
from airflow.models import DagRun, TaskInstance
from airflow.api.common.experimental.trigger_dag import trigger_dag

logger = structlog.get_logger("flowetl")

# pylint: disable=unused-argument
def dummy__callable(*, dag_run: DagRun, task_instance: TaskInstance, **kwargs):
    """
    Dummy python callable - raises an exception if the environment variable
    TASK_TO_FAIL is set to the name of the current task, otherwise succeeds
    silently.
    """
    logger.info(dag_run)
    if os.environ.get("TASK_TO_FAIL", "") == task_instance.task_id:
        raise Exception


def dummy_failing__callable(*, dag_run: DagRun, **kwargs):
    """
    Dummy python callable raising an exception
    """
    logger.info(dag_run)
    raise Exception


def dummy_trigger__callable(*, dag_run: DagRun, **kwargs):
    """
    In test env we just want to trigger the etl_testing DAG with
    no config.
    """
    logger.info(dag_run)
    trigger_dag("etl_testing", run_id=str(uuid1()), execution_date=utcnow())