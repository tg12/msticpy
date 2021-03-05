# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Data driver base class."""
import abc
from abc import ABC
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Union

import pandas as pd

from ..._version import VERSION
from ..query_source import QuerySource

__version__ = VERSION
__author__ = "Ian Hellen"


class DriverBase(ABC):
    """Base class for data providers."""

    def __init__(self, **kwargs):
        """Initialize new instance."""
        self._kwargs = kwargs
        self._loaded = False
        self._connected = False
        self.current_connection = None
        self.public_attribs: Dict[str, Any] = {}
        self.formatters: Dict[str, Callable] = {}
        self.use_query_paths = True
        self.has_driver_queries = False

    @property
    def loaded(self) -> bool:
        """
        Return true if the provider is loaded.

        Returns
        -------
        bool
            True if the provider is loaded.

        Notes
        -----
        This is not relevant for some providers.

        """
        return self._loaded

    @property
    def connected(self) -> bool:
        """
        Return true if at least one connection has been made.

        Returns
        -------
        bool
            True if a successful connection has been made.

        Notes
        -----
        This does not guarantee that the last data source
        connection was successful. It is a best effort to track
        whether the provider has made at least one successful
        authentication.

        """
        return self._connected

    @property
    def schema(self) -> Dict[str, Dict]:
        """
        Return current data schema of connection.

        Returns
        -------
        Dict[str, Dict]
            Data schema of current connection.

        """
        return {}

    @abc.abstractmethod
    def connect(self, connection_str: Optional[str] = None, **kwargs):
        """
        Connect to data source.

        Parameters
        ----------
        connection_str : Optional[str]
            Connect to a data source

        """
        return None

    @abc.abstractmethod
    def query(
        self, query: str, query_source: QuerySource = None, **kwargs
    ) -> Union[pd.DataFrame, Any]:
        """
        Execute query string and return DataFrame of results.

        Parameters
        ----------
        query : str
            The query to execute
        query_source : QuerySource
            The query definition object

        Other Parameters
        ----------------
        kwargs :
            Are passed to the underlying provider query method,
            if supported.

        Returns
        -------
        Union[pd.DataFrame, Any]
            A DataFrame (if successfull) or
            the underlying provider result if an error.

        """

    @abc.abstractmethod
    def query_with_results(self, query: str, **
                           kwargs) -> Tuple[pd.DataFrame, Any]:
        """
        Execute query string and return DataFrame plus native results.

        Parameters
        ----------
        query : str
            The query to execute

        Returns
        -------
        Tuple[pd.DataFrame,Any]
            A DataFrame and native results.

        """

    @property
    def service_queries(self) -> Tuple[Dict[str, str], str]:
        """
        Return queries retrieved from the service after connecting.

        Returns
        -------
        Tuple[Dict[str, str], str]
            Dictionary of query_name, query_text.
            Name of container to add queries to.

        """
        return {}, ""

    @property
    def driver_queries(self) -> Iterable[Dict[str, Any]]:
        """
        Return queries retrieved from the service after connecting.

        Returns
        -------
        List[Dict[str, str]]
            List of Dictionary of query_name, query_text.
            Name of container to add queries to.

        """
        return [{}]
