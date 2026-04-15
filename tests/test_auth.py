"""Tests for auth.py — authentication module structure and helpers."""

import auth


class TestModuleConstants:

    def test_is_databricks_app_is_bool(self):
        assert isinstance(auth.IS_DATABRICKS_APP, bool)

    def test_local_mode_in_tests(self):
        # CI has no DATABRICKS_CLIENT_SECRET, so we should be in local mode
        assert auth.IS_DATABRICKS_APP is False

    def test_default_profile_is_string(self):
        assert isinstance(auth.DATABRICKS_PROFILE, str)
        assert len(auth.DATABRICKS_PROFILE) > 0


class TestMakeApiCall:

    def test_returns_dict(self):
        # Call with an unreachable host — should return error dict, not raise
        result = auth.make_api_call(
            "GET", "/api/2.0/clusters/list", "fake-token",
            "https://127.0.0.1:1", timeout=1,
        )
        assert isinstance(result, dict)
        assert "success" in result
        assert "status_code" in result
        assert result["success"] is False

    def test_result_keys(self):
        result = auth.make_api_call(
            "GET", "/test", "fake", "https://127.0.0.1:1", timeout=1,
        )
        for key in ("status_code", "elapsed_ms", "data", "success"):
            assert key in result, f"Missing key '{key}' in result"
