"""Smoke tests for meok-eu-mobility-package-mcp."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import date, timedelta
from server import (
    check_drivers_hours_eu, check_return_to_base_4w, check_vehicle_return_to_base_8w,
    check_cabotage_3in7, check_smart_tachograph_2_v2, check_imi_posted_worker_declaration,
    check_working_time_directive, generate_eu_compliance_pack, check_eu_aetr_third_country,
    EU_561_LIMITS, CABOTAGE_LIMITS, AETR_COUNTRIES,
)


def _call(t, **kw):
    fn = t.fn if hasattr(t, "fn") else t
    return fn(**kw)


def test_drivers_hours_clean_week():
    r = _call(check_drivers_hours_eu, driver_name="Hans",
              daily_segments=[{"date": "2026-06-08", "driving_hr": 8,
                               "longest_drive_min": 240, "break_min": 45, "daily_rest_hr": 11}])
    assert r["infringement_count"] == 0


def test_drivers_hours_56h_breach():
    days = [{"date": "2026-06-02", "driving_hr": 11}] + [
        {"date": f"2026-06-0{d+3}", "driving_hr": 10} for d in range(5)
    ]
    r = _call(check_drivers_hours_eu, driver_name="Klaus",
              daily_segments=days)
    codes = [i["code"] for i in r["infringements"]]
    assert "exceeded_56h_weekly" in codes
    assert "exceeded_10h_extended" in codes


def test_return_to_base_4w_compliant():
    movements = [{"start": "2026-05-20", "end": "2026-05-22", "country_iso": "DE"}]
    r = _call(check_return_to_base_4w, driver_name="A", base_country_iso="DE",
              movements=movements, as_of="2026-06-08")
    assert r["compliant"] is True
    assert r["days_since_last_return"] <= 28


def test_return_to_base_4w_violation():
    movements = [{"start": "2026-04-01", "end": "2026-04-03", "country_iso": "DE"}]
    r = _call(check_return_to_base_4w, driver_name="B", base_country_iso="DE",
              movements=movements, as_of="2026-06-08")
    assert r["compliant"] is False
    assert r["days_since_last_return"] > 28


def test_return_to_base_4w_no_data():
    r = _call(check_return_to_base_4w, driver_name="C", base_country_iso="PL",
              movements=[], as_of="2026-06-08")
    assert r["compliant"] is False


def test_vehicle_return_to_base_8w_compliant():
    r = _call(check_vehicle_return_to_base_8w, vrn="DE-AB-1234",
              base_country_iso="DE",
              last_seen_at_base="2026-05-20", as_of="2026-06-08")
    assert r["compliant"] is True


def test_vehicle_return_to_base_8w_violation():
    r = _call(check_vehicle_return_to_base_8w, vrn="DE-CD-5678",
              base_country_iso="DE",
              last_seen_at_base="2026-02-01", as_of="2026-06-08")
    assert r["compliant"] is False


def test_cabotage_3in7_compliant():
    r = _call(check_cabotage_3in7, vrn="FR-AB-1234",
              last_international_unload_date="2026-06-01",
              operations_in_country=[
                  {"date": "2026-06-02"}, {"date": "2026-06-04"}
              ],
              cabotage_country_iso="FR")
    assert r["compliant"] is True
    assert r["operations_in_7day_window"] == 2


def test_cabotage_3in7_violation():
    r = _call(check_cabotage_3in7, vrn="FR-EX-9999",
              last_international_unload_date="2026-06-01",
              operations_in_country=[
                  {"date": "2026-06-02"}, {"date": "2026-06-04"},
                  {"date": "2026-06-05"}, {"date": "2026-06-06"}
              ],
              cabotage_country_iso="FR")
    assert r["compliant"] is False
    assert r["operations_in_7day_window"] == 4


def test_smart_tacho_2_lcv_intl_flagged():
    r = _call(check_smart_tachograph_2_v2,
              vehicles=[{"vrn": "PL-1", "type": "lcv_2_5_3_5t",
                         "tacho_gen": "smart_g1", "international_use": True}])
    assert len(r["needs_retrofit"]) == 1


def test_smart_tacho_2_g2v2_already_safe():
    r = _call(check_smart_tachograph_2_v2,
              vehicles=[{"vrn": "DE-1", "type": "hgv_gt_3_5t",
                         "tacho_gen": "smart_g2v2", "international_use": True}])
    assert len(r["needs_retrofit"]) == 0


def test_imi_declaration_cabotage_required():
    r = _call(check_imi_posted_worker_declaration,
              driver_name="Pawel", operation_type="cabotage",
              host_member_state_iso="DE", declaration_filed=False)
    assert r["declaration_required"] is True
    assert r["compliant"] is False


def test_imi_declaration_bilateral_exempt():
    r = _call(check_imi_posted_worker_declaration,
              driver_name="Marek", operation_type="bilateral_transport",
              host_member_state_iso="FR", declaration_filed=False)
    assert r["declaration_required"] is False
    assert r["compliant"] is True


def test_imi_declaration_cross_trade_with_declaration():
    r = _call(check_imi_posted_worker_declaration,
              driver_name="Ivan", operation_type="cross_trade",
              host_member_state_iso="BE", declaration_filed=True)
    assert r["compliant"] is True


def test_working_time_average_breach():
    r = _call(check_working_time_directive, driver_name="X",
              weekly_hours=[50, 52, 49, 51, 50])
    assert len(r["issues"]) >= 1


def test_working_time_within_cap():
    r = _call(check_working_time_directive, driver_name="Y",
              weekly_hours=[45, 47, 44, 48, 46])
    assert r["compliant"] is True


def test_working_time_max_60h_breach():
    r = _call(check_working_time_directive, driver_name="Z",
              weekly_hours=[40, 65, 42, 38])
    assert any("60h" in i for i in r["issues"])


def test_compliance_pack_has_11_sections():
    r = _call(generate_eu_compliance_pack, operator_name="ACME EU",
              operator_country="DE", fleet_size=30,
              cross_border_intensity_pct=70.0)
    assert len(r["evidence_sections"]) == 11
    assert any("Smart Tacho" in s["section"] for s in r["evidence_sections"])


def test_aetr_route_with_turkey():
    r = _call(check_eu_aetr_third_country, driver_name="A",
              route_countries_iso=["DE", "BG", "TR"])
    assert "TR" in r["aetr_countries_on_route"]
    assert r["dual_regime_required"] is True


def test_aetr_route_eu_only():
    r = _call(check_eu_aetr_third_country, driver_name="B",
              route_countries_iso=["DE", "AT", "IT"])
    assert r["aetr_countries_on_route"] == []
    assert r["dual_regime_required"] is False


def test_attestation_chain():
    r = _call(check_drivers_hours_eu, driver_name="K", daily_segments=[])
    assert "sig" in r and "ts" in r
    assert r["issuer"] == "meok-eu-mobility-package-mcp"


def test_aetr_table_includes_known_countries():
    for c in ["TR", "RU", "BY", "UA"]:
        assert c in AETR_COUNTRIES


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
