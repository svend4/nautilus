"""Tests for health_check functions."""
import pytest
from portal import NautilusPortal
from health_check import check_adapters, check_passports, check_consensus, score


@pytest.fixture
def portal():
    return NautilusPortal()


class TestCheckAdapters:
    def test_returns_dict_per_adapter(self, portal):
        results = check_adapters(portal)
        assert set(results.keys()) == set(portal.adapters.keys())

    def test_each_result_has_ok_key(self, portal):
        for name, r in check_adapters(portal).items():
            assert "ok" in r, f"Adapter {name} missing 'ok'"

    def test_successful_adapters_have_entry_counts(self, portal):
        for name, r in check_adapters(portal).items():
            if r["ok"]:
                assert "entries_total" in r
                assert "entries_real" in r
                assert r["entries_real"] + r["entries_fallback"] == r["entries_total"]


class TestCheckPassports:
    def test_returns_dict(self):
        result = check_passports()
        assert isinstance(result, dict)

    def test_no_error_key_when_nautilus_json_exists(self):
        result = check_passports()
        assert "error" not in result


class TestCheckConsensus:
    def test_returns_known_queries(self, portal):
        results = check_consensus(portal)
        for key in ("knowledge", "синтез", "bidir"):
            assert key in results

    def test_coverage_bounds(self, portal):
        for query, r in check_consensus(portal).items():
            assert 0.0 <= r["coverage_real"] <= 1.0
            assert 0.0 <= r["coverage_fallback"] <= 1.0

    def test_ok_field_consistent(self, portal):
        for query, r in check_consensus(portal).items():
            if r["ok"]:
                assert r["coverage_real"] >= 0


class TestScore:
    def test_perfect_score_no_issues(self):
        sc, issues = score({}, {}, {})
        assert sc == 100
        assert issues == []

    def test_failed_adapter_reduces_score(self):
        sc, issues = score({"a": {"ok": False}}, {}, {})
        assert sc < 100
        assert any("❌" in i for i in issues)

    def test_missing_passport_reduces_score(self):
        sc, issues = score({}, {"fmt": {"exists": False}}, {})
        assert sc < 100
        assert any("❌" in i for i in issues)

    def test_low_consensus_reduces_score(self):
        sc, issues = score({}, {}, {"q": {"ok": False}})
        assert sc < 100
        assert any("⚠️" in i for i in issues)

    def test_score_never_negative(self):
        many_failures = {f"a{i}": {"ok": False} for i in range(20)}
        sc, _ = score(many_failures, {}, {})
        assert sc == 0
