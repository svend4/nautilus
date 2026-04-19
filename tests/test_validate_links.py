"""Tests for validate_links."""
import pytest
from portal import NautilusPortal
from validate_links import validate


@pytest.fixture
def portal():
    return NautilusPortal()


class TestValidateLinks:
    def test_no_errors(self, portal):
        report = validate(portal)
        assert report["errors"] == 0

    def test_no_warnings(self, portal):
        report = validate(portal)
        assert report["warnings"] == 0, (
            f"Expected 0 warnings, got {report['warnings']}:\n"
            + "\n".join(f"  {b['link']} <- {b['source']}" for b in report["broken"])
        )

    def test_report_ok(self, portal):
        report = validate(portal)
        assert report["ok"] is True

    def test_all_links_valid(self, portal):
        report = validate(portal)
        assert report["valid_links"] == report["total_links"]

    def test_entries_collected(self, portal):
        report = validate(portal)
        assert report["total_entries"] > 50
