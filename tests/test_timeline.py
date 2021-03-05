# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
import unittest
from pathlib import Path

import nbformat
import notebook
import pytest
from nbconvert.preprocessors import CellExecutionError, ExecutePreprocessor

_NB_FOLDER = "docs/notebooks"
_NB_NAME = "EventTimeline.ipynb"


class TestTimeline(unittest.TestCase):
    """Unit test class."""

    @pytest.mark.skipif(not os.environ.get("MSTICPY_TEST_NOSKIP"),
                        reason="Skipped for local tests.")
    def test_timeline_controls(self):
        nb_path = Path(_NB_FOLDER).joinpath(_NB_NAME)
        abs_path = Path(_NB_FOLDER).absolute()
        with open(nb_path) as f:
            nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

        try:
            ep.preprocess(nb, {"metadata": {"path": abs_path}})
        except CellExecutionError:
            nb_err = str(nb_path).replace(".ipynb", "-err.ipynb")
            msg = f"Error executing the notebook '{nb_path}'.\n"
            msg += f"See notebook '{nb_err}' for the traceback."
            print(msg)
            with open(nb_err, mode="w", encoding="utf-8") as f:
                nbformat.write(nb, f)
            raise
