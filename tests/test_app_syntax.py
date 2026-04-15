"""Syntax and import checks for all Python modules."""

import py_compile
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY_FILES = sorted(ROOT.glob("*.py"))


@pytest.mark.parametrize("path", PY_FILES, ids=[p.name for p in PY_FILES])
def test_syntax(path):
    """Every .py file must be valid Python."""
    py_compile.compile(str(path), doraise=True)


def test_api_catalog_imports():
    """api_catalog.py must load without error."""
    import api_catalog
    assert hasattr(api_catalog, "API_CATALOG")
    assert hasattr(api_catalog, "ENDPOINT_MAP")


def test_auth_imports():
    """auth.py must load without error."""
    import auth
    assert hasattr(auth, "make_api_call")
    assert hasattr(auth, "IS_DATABRICKS_APP")


def test_version_module():
    """version.py must expose BUILD and VERSION."""
    import version
    assert isinstance(version.BUILD, int)
    assert version.VERSION.startswith("v")
