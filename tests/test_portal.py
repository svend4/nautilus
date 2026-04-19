"""Tests for NautilusPortal and rendering functions."""
import pytest
from portal import NautilusPortal, PortalResult, render_text, render_html


@pytest.fixture
def portal():
    return NautilusPortal()


class TestNautilusPortal:
    def test_adapters_loaded(self, portal):
        assert len(portal.adapters) >= 7
        for name in ("info1", "pro2", "meta", "data2", "data7", "infosystems", "ai_agents"):
            assert name in portal.adapters

    def test_query_returns_result(self, portal):
        result = portal.query("knowledge")
        assert isinstance(result, PortalResult)
        assert result.query == "knowledge"

    def test_query_has_entries(self, portal):
        result = portal.query("knowledge")
        assert len(result.entries) > 0

    def test_query_consensus_structure(self, portal):
        result = portal.query("синтез")
        c = result.consensus
        assert "coverage" in c
        assert "coverage_with_fallback" in c
        assert "present_in" in c
        assert "missing_in" in c
        assert 0.0 <= c["coverage"] <= 1.0

    def test_real_vs_fallback_coverage(self, portal):
        result = portal.query("knowledge")
        c = result.consensus
        # Real coverage must be ≤ coverage_with_fallback
        assert c["coverage"] <= c["coverage_with_fallback"]

    def test_unknown_query_coverage_near_zero(self, portal):
        result = portal.query("zzz_completely_unknown_xqz")
        c = result.consensus
        assert c["coverage"] == 0.0

    def test_cross_links_are_cross_repo(self, portal):
        result = portal.query("синтез")
        for link in result.cross_links:
            assert link["from_repo"] != link["to_repo"]

    def test_describe_returns_all_adapters(self, portal):
        desc = portal.describe()
        assert set(desc.keys()) == set(portal.adapters.keys())

    def test_register_custom_adapter(self, portal):
        from adapters.base import BaseAdapter, PortalEntry

        class DummyAdapter(BaseAdapter):
            name = "dummy"
            def fetch(self, query):
                return [PortalEntry("dummy:1", "Test", "test/repo", "doc", "content")]
            def describe(self):
                return {"format": "dummy"}

        portal.register("dummy", DummyAdapter())
        assert "dummy" in portal.adapters
        result = portal.query("content")
        assert any(e.id == "dummy:1" for e in result.entries)


class TestRenderText:
    def test_render_text_contains_query(self, portal):
        result = portal.query("котёл")
        text = render_text(result)
        assert "котёл" in text.lower()

    def test_render_text_has_consensus_line(self, portal):
        result = portal.query("knowledge")
        text = render_text(result)
        assert "Консенсус" in text

    def test_render_text_includes_entries(self, portal):
        result = portal.query("синтез")
        text = render_text(result)
        assert len(text) > 100


class TestRenderHtml:
    def test_render_html_is_valid(self, portal):
        result = portal.query("knowledge")
        html = render_html(result, portal)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_render_html_escapes_xss(self, portal):
        from adapters.base import PortalEntry
        malicious = PortalResult(
            query="<script>alert(1)</script>",
            entries=[PortalEntry(
                id="test:1", title="<b>bold</b>",
                source="test", format_type="doc",
                content="<img onerror=alert(1)>",
            )],
            cross_links=[],
            consensus={"coverage": 0, "coverage_with_fallback": 0,
                       "present_in": [], "missing_in": []},
        )
        html = render_html(malicious, portal)
        assert "<script>" not in html
        assert "<b>bold</b>" not in html
        assert "&lt;script&gt;" in html

    def test_render_html_contains_adapters_list(self, portal):
        result = portal.query("knowledge")
        html = render_html(result, portal)
        assert "info1" in html
        assert "pro2" in html
