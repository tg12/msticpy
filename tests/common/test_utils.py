# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""vtlookup test class."""
from pathlib import Path
import unittest

import pytest_check as check

from msticpy.nbtools import utils


class TestUtils(unittest.TestCase):
    """Unit test class."""

    def test_misc_funcs(self):
        self.assertTrue(utils.string_empty(None))
        self.assertTrue(utils.string_empty(""))

        self.assertFalse(utils.is_not_empty(None))
        self.assertFalse(utils.is_not_empty(""))
        self.assertFalse(utils.is_not_empty({}))

        self.assertEqual(
            utils.escape_windows_path("C:\\windows"),
            "C:\\\\windows")
        self.assertEqual(utils.escape_windows_path("C:/windows"), "C:/windows")

        self.assertEqual(
            utils.unescape_windows_path("C:\\\\windows"),
            "C:\\windows")
        self.assertEqual(
            utils.unescape_windows_path("C:/windows"),
            "C:/windows")

        with self.assertRaises(SystemExit):
            utils.check_py_version((4, 0))
        utils.check_py_version((3, 6))
        utils.check_py_version(3.6)
        utils.check_py_version("3.6")

        abs_path = "/etc" if Path("/etc").is_absolute() else "c:\\windows"
        self.assertEqual(utils.resolve_pkg_path(abs_path), abs_path)
        self.assertIsNotNone(utils.resolve_pkg_path("sectools"))
        with self.assertWarns(UserWarning):
            utils.resolve_pkg_path("somefakefolder")

    def test_md(self):
        utils.md("test")
        utils.md("test", "red, bold")
        utils.md("test", ["red", "bold"])

    def test_kwarg_check(self):
        _DEFAULT_KWARGS = [
            "color",
            "data",
            "group_by",
            "height",
            "legend",
            "range_tool",
            "ref_event",
            "ref_time",
            "source_columns",
            "time_column",
            "title",
            "width",
            "yaxis",
        ]

        args_ok = {"color": "red"}
        args_bad = {"color": "red", "datum": "dframe"}
        args2_bad = {"color": "red", "columns": "dframe", "datum": "dframe"}

        utils.check_kwargs(args_ok, _DEFAULT_KWARGS)
        try:
            utils.check_kwargs(args_bad, _DEFAULT_KWARGS)
        except NameError as err:
            self.assertIsNotNone(err)
            self.assertIn("datum", err.args[0][0].args)
        try:
            utils.check_kwargs(args2_bad, _DEFAULT_KWARGS)
        except NameError as err:
            self.assertEqual(len(err.args[0]), 2)
            self.assertIn("columns", err.args[0][0].args)
            self.assertIn("source_columns", err.args[0][0].args[1])
            self.assertIn("time_column", err.args[0][0].args[1])
            self.assertIn("datum", err.args[0][1].args)


def test_format_py_identifier():
    """Test replacing illegal chars in identifier."""
    check.equal(utils.valid_pyname("legal"), "legal")
    check.equal(utils.valid_pyname("open"), "open_bi")
    check.equal(utils.valid_pyname("has space"), "has_space")
    check.equal(utils.valid_pyname("has-dash"), "has_dash")
    check.equal(utils.valid_pyname("10.starts,digit$"), "n_10_starts_digit_")
