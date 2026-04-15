"""Tests for api_catalog.py — endpoint definitions and chip extraction."""

import pytest
from api_catalog import (
    API_CATALOG,
    ACCOUNT_API_CATALOG,
    ENDPOINT_MAP,
    LIST_TO_GET,
    ACCOUNT_LIST_TO_GET,
    TOTAL_ENDPOINTS,
    TOTAL_CATEGORIES,
    TOTAL_ACCOUNT_ENDPOINTS,
    TOTAL_ACCOUNT_CATEGORIES,
    extract_chips,
)

REQUIRED_ENDPOINT_KEYS = {"id", "name", "method", "path"}
VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


# ── Catalog structure ────────────────────────────────────────────────────────

class TestCatalogStructure:
    """Every category must have icon, color, and a non-empty endpoints list."""

    @pytest.mark.parametrize("catalog_name,catalog", [
        ("workspace", API_CATALOG),
        ("account", ACCOUNT_API_CATALOG),
    ])
    def test_categories_have_required_fields(self, catalog_name, catalog):
        for cat_name, cat in catalog.items():
            assert "icon" in cat, f"{catalog_name}/{cat_name}: missing 'icon'"
            assert "color" in cat, f"{catalog_name}/{cat_name}: missing 'color'"
            assert "endpoints" in cat, f"{catalog_name}/{cat_name}: missing 'endpoints'"
            assert len(cat["endpoints"]) > 0, f"{catalog_name}/{cat_name}: empty endpoints list"

    def test_totals_are_positive(self):
        assert TOTAL_ENDPOINTS > 0
        assert TOTAL_CATEGORIES > 0
        assert TOTAL_ACCOUNT_ENDPOINTS > 0
        assert TOTAL_ACCOUNT_CATEGORIES > 0


# ── Endpoint definitions ─────────────────────────────────────────────────────

def _all_endpoints():
    """Yield (scope, category, endpoint) for every endpoint in both catalogs."""
    for cat_name, cat in API_CATALOG.items():
        for ep in cat["endpoints"]:
            yield "workspace", cat_name, ep
    for cat_name, cat in ACCOUNT_API_CATALOG.items():
        for ep in cat["endpoints"]:
            yield "account", cat_name, ep


class TestEndpointDefinitions:

    @pytest.mark.parametrize("scope,category,ep", list(_all_endpoints()),
                             ids=[f"{s}/{c}/{e['id']}" for s, c, e in _all_endpoints()])
    def test_required_keys(self, scope, category, ep):
        missing = REQUIRED_ENDPOINT_KEYS - ep.keys()
        assert not missing, f"{scope}/{category}/{ep.get('id', '?')}: missing keys {missing}"

    @pytest.mark.parametrize("scope,category,ep", list(_all_endpoints()),
                             ids=[f"{s}/{c}/{e['id']}" for s, c, e in _all_endpoints()])
    def test_valid_method(self, scope, category, ep):
        assert ep["method"] in VALID_METHODS, (
            f"{ep['id']}: invalid method '{ep['method']}'"
        )

    @pytest.mark.parametrize("scope,category,ep", list(_all_endpoints()),
                             ids=[f"{s}/{c}/{e['id']}" for s, c, e in _all_endpoints()])
    def test_path_starts_with_slash(self, scope, category, ep):
        assert ep["path"].startswith("/"), f"{ep['id']}: path must start with '/'"

    @pytest.mark.parametrize("scope,category,ep", list(_all_endpoints()),
                             ids=[f"{s}/{c}/{e['id']}" for s, c, e in _all_endpoints()])
    def test_params_are_well_formed(self, scope, category, ep):
        for param in ep.get("params", []):
            assert "name" in param, f"{ep['id']}: param missing 'name'"
            assert "description" in param, f"{ep['id']}/{param['name']}: missing 'description'"

    def test_no_duplicate_endpoint_ids(self):
        seen = {}
        for scope, cat, ep in _all_endpoints():
            eid = ep["id"]
            assert eid not in seen, f"Duplicate endpoint ID '{eid}' in {scope}/{cat} and {seen[eid]}"
            seen[eid] = f"{scope}/{cat}"

    def test_path_params_match_path(self):
        """path_params entries must correspond to {placeholders} in the path."""
        for scope, cat, ep in _all_endpoints():
            path_params = ep.get("path_params", [])
            import re
            placeholders = set(re.findall(r"\{(\w+)\}", ep["path"]))
            for pp in path_params:
                assert pp in placeholders, (
                    f"{ep['id']}: path_param '{pp}' not found in path '{ep['path']}'"
                )


# ── ENDPOINT_MAP ─────────────────────────────────────────────────────────────

class TestEndpointMap:

    def test_map_contains_all_endpoints(self):
        ids_from_catalogs = {ep["id"] for _, _, ep in _all_endpoints()}
        ids_from_map = set(ENDPOINT_MAP.keys())
        assert ids_from_catalogs == ids_from_map

    def test_map_entries_have_scope(self):
        for eid, ep in ENDPOINT_MAP.items():
            assert ep.get("scope") in ("workspace", "account"), (
                f"{eid}: missing or invalid scope"
            )

    def test_map_entries_have_category(self):
        for eid, ep in ENDPOINT_MAP.items():
            assert "category" in ep, f"{eid}: missing category"
            assert "category_color" in ep, f"{eid}: missing category_color"


# ── LIST_TO_GET link maps ────────────────────────────────────────────────────

class TestListToGet:

    @pytest.mark.parametrize("map_name,link_map", [
        ("LIST_TO_GET", LIST_TO_GET),
        ("ACCOUNT_LIST_TO_GET", ACCOUNT_LIST_TO_GET),
    ])
    def test_list_ids_exist(self, map_name, link_map):
        for list_id in link_map:
            assert list_id in ENDPOINT_MAP, (
                f"{map_name}: list endpoint '{list_id}' not in ENDPOINT_MAP"
            )

    @pytest.mark.parametrize("map_name,link_map", [
        ("LIST_TO_GET", LIST_TO_GET),
        ("ACCOUNT_LIST_TO_GET", ACCOUNT_LIST_TO_GET),
    ])
    def test_get_ids_exist(self, map_name, link_map):
        for list_id, entry in link_map.items():
            get_id = entry[0]
            assert get_id in ENDPOINT_MAP, (
                f"{map_name}: get endpoint '{get_id}' (from '{list_id}') not in ENDPOINT_MAP"
            )


# ── extract_chips ────────────────────────────────────────────────────────────

class TestExtractChips:

    def test_returns_list(self):
        result = extract_chips("nonexistent-id", {"items": []})
        assert isinstance(result, list)

    def test_chips_from_known_list(self):
        # clusters-list is linked to clusters-get
        fake_data = {"clusters": [
            {"cluster_id": "abc-123", "cluster_name": "test-cluster"},
        ]}
        chips = extract_chips("clusters-list", fake_data)
        assert len(chips) > 0
        chip = chips[0]
        assert "get_id" in chip
        assert "id_field" in chip
        assert "value" in chip
        assert chip["value"] == "abc-123"
        assert chip["get_id"] == "clusters-get"
