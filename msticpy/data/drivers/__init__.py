# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Data provider sub-package."""
import importlib
from typing import Union

from ..query_defns import DataEnvironment

# flake8: noqa: F403
from .driver_base import DriverBase

from ..._version import VERSION

__version__ = VERSION

_ENVIRONMENT_DRIVERS = {
    DataEnvironment.LogAnalytics: ("kql_driver", "KqlDriver"),
    DataEnvironment.AzureSecurityCenter: ("kql_driver", "KqlDriver"),
    DataEnvironment.SecurityGraph: ("security_graph_driver", "SecurityGraphDriver"),
    DataEnvironment.MDATP: ("mdatp_driver", "MDATPDriver"),
    DataEnvironment.MDE: ("mdatp_driver", "MDATPDriver"),
    DataEnvironment.LocalData: ("local_data_driver", "LocalDataDriver"),
    DataEnvironment.Splunk: ("splunk_driver", "SplunkDriver"),
    DataEnvironment.Mordor: ("mordor_driver", "MordorDriver"),
}


def import_driver(data_environment: DataEnvironment) -> type:
    """Import driver class for a data environment."""
    mod_name, cls_name = _ENVIRONMENT_DRIVERS.get(
        data_environment, (None, None))

    if not (mod_name and cls_name):
        raise ValueError(
            f"No driver available for environment {data_environment.name}.",
            "Possible values are:",
            ", ".join(env.name for env in _ENVIRONMENT_DRIVERS),
        )

    imp_module = importlib.import_module(
        f"msticpy.data.drivers.{mod_name}", package="msticpy"
    )
    return getattr(imp_module, cls_name)
