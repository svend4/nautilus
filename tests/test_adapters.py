"""Tests for individual adapters."""
import pytest
from adapters.base import PortalEntry
from adapters.meta import MetaAdapter
from adapters.data2 import Data2Adapter
from adapters.info1 import Info1Adapter
from adapters.pro2 import Pro2Adapter
from adapters.infosystems import InfoSystemsAdapter
from adapters.ai_agents import AIAgentsAdapter


# ── PortalEntry ───────────────────────────────────────────────────────────────

def test_portal_entry_defaults():
    e = PortalEntry(id="x:1", title="T", source="s", format_type="doc", content="c")
    assert e.metadata == {}
    assert e.links == []
    assert e.is_fallback is False


def test_portal_entry_fallback_flag():
    e = PortalEntry(id="x:1", title="T", source="s", format_type="doc", content="c",
                    is_fallback=True)
    assert e.is_fallback is True


# ── MetaAdapter ───────────────────────────────────────────────────────────────

class TestMetaAdapter:
    def setup_method(self):
        self.a = MetaAdapter()

    def test_fetch_returns_entries(self):
        entries = self.a.fetch("котёл")
        assert len(entries) > 0

    def test_fetch_result_has_q6(self):
        entries = self.a.fetch("котёл")
        assert any(e.metadata.get("q6") for e in entries)

    def test_fetch_fallback_on_unknown(self):
        entries = self.a.fetch("xyzzy_nonexistent_42")
        assert len(entries) > 0
        assert all(e.is_fallback for e in entries[:4])

    def test_index_entries_always_present(self):
        entries = self.a.fetch("")
        ids = {e.id for e in entries}
        assert "meta:hexagram:all" in ids
        assert "meta:ca_rules" in ids
        for cls in ("I", "II", "III", "IV"):
            assert f"meta:ca_class:{cls}" in ids

    def test_hexagram_entry_has_links(self):
        entries = self.a.fetch("котёл")
        e = next(e for e in entries if "hexagram:50" in e.id)
        assert len(e.links) >= 2

    def test_describe_keys(self):
        d = self.a.describe()
        assert "repo" in d and "format" in d and "native_unit" in d


# ── Data2Adapter ──────────────────────────────────────────────────────────────

class TestData2Adapter:
    def setup_method(self):
        self.a = Data2Adapter()

    def test_fetch_archetype(self):
        entries = self.a.fetch("петля")
        assert any("arch" in e.id for e in entries)

    def test_fetch_volume(self):
        entries = self.a.fetch("синтез")
        assert any("vol" in e.id for e in entries)

    def test_fallback_on_unknown(self):
        entries = self.a.fetch("zzz_unknown_999")
        assert len(entries) > 0

    def test_entries_have_q6(self):
        for entry in self.a.fetch("синтез"):
            assert "q6" in entry.metadata or entry.is_fallback

    def test_describe_has_archetypes(self):
        d = self.a.describe()
        assert "archetypes_12" in d
        assert len(d["archetypes_12"]) > 0


# ── Info1Adapter ──────────────────────────────────────────────────────────────

class TestInfo1Adapter:
    def setup_method(self):
        self.a = Info1Adapter()

    def test_static_includes_methodology(self):
        entries = self.a._static_entries()
        ids = {e.id for e in entries}
        assert "info1:methodology" in ids

    def test_alpha_entries_present(self):
        entries = self.a._static_entries()
        ids = {e.id for e in entries}
        for alpha in (-3, -1, 0, 1, 3):
            assert f"info1:alpha:{alpha}" in ids

    def test_fetch_falls_back_gracefully(self):
        entries = self.a.fetch("nonexistent_xyz")
        assert len(entries) > 0

    def test_alpha_entry_has_correct_level(self):
        entries = self.a._static_entries()
        e = next(e for e in entries if e.id == "info1:alpha:3")
        assert e.metadata["alpha"] == 3


# ── Pro2Adapter ───────────────────────────────────────────────────────────────

class TestPro2Adapter:
    def setup_method(self):
        self.a = Pro2Adapter()

    def test_static_entries_include_q6(self):
        entries = self.a._static_entries()
        ids = {e.id for e in entries}
        assert "pro2:q6" in ids

    def test_q6_bit_entries_present(self):
        entries = self.a._static_entries()
        ids = {e.id for e in entries}
        for bits in ("000000", "111111", "110001"):
            assert f"pro2:q6:{bits}" in ids

    def test_all_component_ids_present(self):
        entries = self.a._static_entries()
        ids = {e.id for e in entries}
        for expected in ("pro2:bidir", "pro2:moe", "pro2:biangua",
                         "pro2:self_train", "pro2:nautilus"):
            assert expected in ids, f"Missing: {expected}"

    def test_q6_entry_has_valid_metadata(self):
        e = self.a._q6_entry("110001")
        assert e.metadata["q6"] == "110001"
        assert e.id == "pro2:q6:110001"


# ── InfoSystemsAdapter ────────────────────────────────────────────────────────

class TestInfoSystemsAdapter:
    def setup_method(self):
        self.a = InfoSystemsAdapter()

    def test_fetch_domain_moe(self):
        entries = self.a.fetch("moe")
        assert any("domain_moe" in e.id for e in entries)

    def test_fetch_all(self):
        entries = self.a.fetch("all")
        assert len(entries) >= 4

    def test_entries_have_links(self):
        for e in self.a.fetch("all"):
            assert isinstance(e.links, list)


# ── AIAgentsAdapter ───────────────────────────────────────────────────────────

class TestAIAgentsAdapter:
    def setup_method(self):
        self.a = AIAgentsAdapter()

    def test_fetch_bidir(self):
        entries = self.a.fetch("bidir")
        assert any("bidir" in e.id for e in entries)

    def test_fetch_agent(self):
        entries = self.a.fetch("agent")
        assert len(entries) >= 3

    def test_all_entries_have_format(self):
        for e in self.a.fetch("agent"):
            assert e.format_type == "agent_pattern"
