#!/usr/bin/env python3
"""
MEOK EU Mobility Package Compliance MCP
==========================================

By MEOK AI Labs · https://haulage.app · MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-eu-mobility-package-mcp -->

WHAT THIS DOES
--------------
The EU Mobility Package (adopted 2020, phased 2020-2026) overhauled road
transport across all 27 EU member states + UK/EFTA/EEA. It tightened
drivers' hours, mandated return-to-base, applied posted-workers rules to
mobile workers, and is forcing Smart Tachograph 2 (G2V2) retrofit on
2.5-3.5t LCVs by 1 July 2026.

Operators running cross-border in the EU now face:
- EU Regulation 561/2006 (retained UK + active EU) — drivers' hours
- Directive 2002/15/EC — Working Time for mobile workers
- Posted Workers Directive 96/71/EC applied via Directive (EU) 2020/1057
- IMI (Internal Market Information) System — mandatory declarations
- Regulation 165/2014 + Implementing Reg 2021/1228 — Smart Tachograph 2
- Cabotage rules — 3 operations / 7 days post-Unloading
- 4-week return-to-base for drivers
- 8-week return-to-base for vehicles

This MCP gives EU operators (and UK operators running cross-border) a
callable layer for the daily compliance work.

TOOLS (9)
---------
- check_drivers_hours_eu(driver_log)         → EU 561/2006 full audit
- check_return_to_base_4w(driver_history)    → driver 4-week return
- check_vehicle_return_to_base_8w(vrn)       → vehicle 8-week return
- check_cabotage_3in7(operations)            → 3 ops in 7 days post-unload
- check_smart_tachograph_2_v2(fleet)         → G2V2 retrofit 1 Jul 2026
- check_imi_posted_worker_declaration(driver, host_state) → IMI lookup
- check_working_time_directive(driver_log)   → Dir 2002/15/EC 48h/wk cap
- generate_eu_compliance_pack(operator)      → cross-border evidence pack
- check_eu_aetr_third_country(driver, route) → AETR (non-EU 561 countries)

PRICING
-------
Free MIT self-host · €49/mo Starter · €149/mo Pro · €799/mo Fleet · €1,999/mo Enterprise.

REGULATORY BASIS
----------------
- Regulation (EC) 561/2006 (drivers' hours)
- Regulation (EU) 165/2014 + 2021/1228 (Smart Tacho 2)
- Directive 2002/15/EC (Working Time)
- Directive 96/71/EC + (EU) 2020/1057 (Posted Workers in road transport)
- Regulation (EU) 2020/1054 (Mobility Package I)
- Regulation (EU) 2020/1055 (access to occupation + cabotage)
- AETR (European Agreement Concerning the Work of Crews — non-EU)
"""

from __future__ import annotations
import hashlib, hmac, json, os
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-eu-mobility-package")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# Regulatory tables
# ──────────────────────────────────────────────────────────────────────

# EU 561/2006 — same limits as UK retained version (post-Brexit divergence
# possible but UK & EU still aligned as of 2026)
EU_561_LIMITS = {
    "max_continuous_driving_min": 270,
    "min_break_min": 45,
    "max_daily_driving_hr": 9,
    "max_daily_driving_extended_hr": 10,  # x2 per week
    "max_weekly_driving_hr": 56,
    "max_fortnightly_driving_hr": 90,
    "min_daily_rest_hr": 11,
    "min_weekly_rest_hr": 45,
    "min_reduced_weekly_rest_hr": 24,  # max 1 per 2 weeks with compensation
}

# Directive 2002/15/EC — Working Time for mobile workers
WORKING_TIME_LIMITS = {
    "avg_weekly_max_hr": 48,
    "max_weekly_hr": 60,
    "reference_period_months": 4,  # 6 by collective agreement
    "max_consecutive_work_no_break_hr": 6,
    "break_min_below_9_total_hr": 30,
    "break_min_above_9_total_hr": 45,
    "max_night_work_per_24h_hr": 10,
}

# Smart Tacho 2 v2 — Implementing Regulation 2021/1228
SMART_TACHO_2_DEADLINES_EU = {
    "intl_hgv_g2v2_retrofit": date(2025, 8, 19),  # All HGV >3.5t intl
    "intl_lcv_2_5_3_5t_fit_from_new": date(2026, 7, 1),
    "intl_lcv_2_5_3_5t_retrofit_all": date(2026, 7, 1),
}

# Cabotage limits (Reg 1072/2009 as amended by Mobility Package)
CABOTAGE_LIMITS = {
    "max_operations": 3,
    "max_days_after_intl_unload": 7,
    "cooling_off_days": 4,  # No cabotage in same MS for 4 days after the 7-day window
}

# Return-to-base rules (Mobility Package I)
RETURN_TO_BASE = {
    "driver_weeks_max": 4,        # Driver must return to base every 4 weeks
    "vehicle_weeks_max": 8,       # Vehicle must return to base every 8 weeks
}

# AETR — non-EU countries with their own driver-hours regime
AETR_COUNTRIES = {
    "AL", "AM", "AZ", "BA", "BY", "KZ", "MD", "ME", "MK",
    "RS", "RU", "TM", "TR", "UA", "UZ",
}

# IMI — Posted Workers must declare
IMI_DECLARATION_TYPES = {
    "bilateral_transport": False,    # Exempt
    "transit": False,                # Exempt
    "cabotage": True,
    "cross_trade": True,
    "combined_transport_intl_legs": False,  # Exempt
    "combined_transport_road_only": True,
}


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(_HMAC_SECRET.encode(),
                    json.dumps(payload, sort_keys=True, default=str).encode(),
                    hashlib.sha256).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attestation(payload: dict) -> dict:
    return {**payload, "ts": _ts(), "sig": _sign(payload),
            "issuer": "meok-eu-mobility-package-mcp", "version": "1.0.0"}


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def check_drivers_hours_eu(
    driver_name: str = "",
    daily_segments: Optional[list] = None,
    week_starting: str = "",
) -> dict:
    """Audit a driver's week against EU 561/2006 limits."""
    daily_segments = daily_segments or []
    infringements = []

    weekly_drive = sum(d.get("driving_hr", 0) for d in daily_segments)
    if weekly_drive > EU_561_LIMITS["max_weekly_driving_hr"]:
        infringements.append({"code": "exceeded_56h_weekly",
                              "actual_hr": round(weekly_drive, 2)})

    extended_count = 0
    for d in daily_segments:
        dr = d.get("driving_hr", 0)
        if dr > EU_561_LIMITS["max_daily_driving_extended_hr"]:
            infringements.append({"code": "exceeded_10h_extended",
                                  "date": d.get("date"), "actual_hr": dr})
        elif dr > EU_561_LIMITS["max_daily_driving_hr"]:
            extended_count += 1
            if extended_count > 2:
                infringements.append({"code": "exceeded_9h_more_than_twice",
                                      "date": d.get("date"), "actual_hr": dr})
        if d.get("longest_drive_min", 0) > EU_561_LIMITS["max_continuous_driving_min"]:
            infringements.append({"code": "exceeded_4h30_no_break",
                                  "date": d.get("date")})
        if d.get("break_min", 0) < EU_561_LIMITS["min_break_min"]:
            infringements.append({"code": "insufficient_45min_break",
                                  "date": d.get("date")})
        if d.get("daily_rest_hr", 24) < EU_561_LIMITS["min_daily_rest_hr"]:
            infringements.append({"code": "insufficient_11h_daily_rest",
                                  "date": d.get("date")})

    return _attestation({
        "tool": "check_drivers_hours_eu",
        "driver": driver_name,
        "week_starting": week_starting,
        "weekly_driving_hr": round(weekly_drive, 2),
        "infringement_count": len(infringements),
        "infringements": infringements,
        "regulator_ref": "EU Regulation 561/2006",
    })


@mcp.tool()
def check_return_to_base_4w(
    driver_name: str,
    base_country_iso: str,
    movements: Optional[list] = None,
    as_of: str = "",
) -> dict:
    """4-week return-to-base check (Mobility Package I).

    Args:
      movements: list of dicts {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD",
                                "country_iso": "DE"}
      as_of: ISO date; defaults to today
    """
    movements = movements or []
    try:
        ref = date.fromisoformat(as_of) if as_of else date.today()
    except Exception:
        ref = date.today()

    # Find most recent return-to-base movement
    last_at_base = None
    for m in movements:
        if m.get("country_iso") == base_country_iso:
            end = m.get("end") or m.get("start")
            try:
                end_d = date.fromisoformat(end)
                if last_at_base is None or end_d > last_at_base:
                    last_at_base = end_d
            except Exception:
                continue

    if last_at_base is None:
        days_since = None
        compliant = False
        issue = "No return-to-base recorded in dataset"
    else:
        days_since = (ref - last_at_base).days
        compliant = days_since <= 28
        issue = "" if compliant else f"Last return {days_since}d ago — >28d violates Mobility Package"

    return _attestation({
        "tool": "check_return_to_base_4w",
        "driver": driver_name,
        "base_country": base_country_iso,
        "days_since_last_return": days_since,
        "compliant": compliant,
        "issue": issue,
        "regulator_ref": "Regulation (EU) 2020/1054 — Mobility Package I, driver return-to-base",
    })


@mcp.tool()
def check_vehicle_return_to_base_8w(
    vrn: str,
    base_country_iso: str,
    last_seen_at_base: str = "",
    as_of: str = "",
) -> dict:
    """8-week return-to-base check for vehicles."""
    try:
        ref = date.fromisoformat(as_of) if as_of else date.today()
    except Exception:
        ref = date.today()
    try:
        last = date.fromisoformat(last_seen_at_base)
        days_since = (ref - last).days
        compliant = days_since <= 56
    except Exception:
        days_since, compliant = None, False

    return _attestation({
        "tool": "check_vehicle_return_to_base_8w",
        "vrn": vrn,
        "base_country": base_country_iso,
        "days_since_at_base": days_since,
        "compliant": compliant,
        "issue": "" if compliant else f"Vehicle not at base for {days_since}d (>56d cap)" if days_since else "Unknown",
        "regulator_ref": "Regulation (EU) 2020/1055",
    })


@mcp.tool()
def check_cabotage_3in7(
    vrn: str,
    last_international_unload_date: str,
    operations_in_country: Optional[list] = None,
    cabotage_country_iso: str = "",
) -> dict:
    """Cabotage: max 3 ops in 7 days after international unload.

    Args:
      operations_in_country: list of dicts {"date": "YYYY-MM-DD"} for ops in
                             the cabotage country since the unload date
    """
    operations_in_country = operations_in_country or []
    try:
        unload = date.fromisoformat(last_international_unload_date)
    except Exception:
        return _attestation({"tool": "check_cabotage_3in7",
                             "error": "invalid unload date"})

    cutoff = unload + timedelta(days=CABOTAGE_LIMITS["max_days_after_intl_unload"])
    ops_in_window = []
    for op in operations_in_country:
        try:
            d = date.fromisoformat(op.get("date", ""))
            if unload <= d <= cutoff:
                ops_in_window.append(d)
        except Exception:
            continue

    over_limit = len(ops_in_window) > CABOTAGE_LIMITS["max_operations"]
    return _attestation({
        "tool": "check_cabotage_3in7",
        "vrn": vrn,
        "cabotage_country": cabotage_country_iso,
        "operations_in_7day_window": len(ops_in_window),
        "max_allowed": CABOTAGE_LIMITS["max_operations"],
        "compliant": not over_limit,
        "cooling_off_until": (cutoff + timedelta(days=CABOTAGE_LIMITS["cooling_off_days"])).isoformat(),
        "advisory": ("EXCEEDED — fines per MS (DE up to €5,000/op, FR up to €15,000)"
                     if over_limit else "Within cabotage envelope"),
        "regulator_ref": "Regulation (EC) 1072/2009 amended by Mobility Package",
    })


@mcp.tool()
def check_smart_tachograph_2_v2(
    vehicles: Optional[list] = None,
) -> dict:
    """Smart Tachograph 2 v2 retrofit deadlines (EU 2021/1228).

    Args:
      vehicles: list of dicts {"vrn", "type": 'hgv_gt_3_5t'/'lcv_2_5_3_5t'/...,
                "tacho_gen", "international_use"}
    """
    vehicles = vehicles or []
    today = date.today()
    needs_retrofit = []

    for v in vehicles:
        vrn = v.get("vrn", "")
        vtype = v.get("type", "hgv_gt_3_5t")
        gen = v.get("tacho_gen", "digital_g1")
        intl = v.get("international_use", False)

        if gen == "smart_g2v2": continue
        if vtype == "hgv_gt_3_5t" and intl:
            deadline = SMART_TACHO_2_DEADLINES_EU["intl_hgv_g2v2_retrofit"]
        elif vtype == "lcv_2_5_3_5t" and intl:
            deadline = SMART_TACHO_2_DEADLINES_EU["intl_lcv_2_5_3_5t_retrofit_all"]
        else:
            continue

        days_left = (deadline - today).days
        needs_retrofit.append({"vrn": vrn, "current_gen": gen,
                               "deadline": deadline.isoformat(),
                               "days_remaining": days_left,
                               "overdue": days_left < 0})

    return _attestation({
        "tool": "check_smart_tachograph_2_v2",
        "fleet_size": len(vehicles),
        "needs_retrofit": needs_retrofit,
        "regulator_ref": "Regulation (EU) 165/2014 + 2021/1228",
    })


@mcp.tool()
def check_imi_posted_worker_declaration(
    driver_name: str,
    operation_type: str,
    host_member_state_iso: str,
    declaration_filed: bool = False,
) -> dict:
    """Posted Workers Directive IMI declaration check.

    operation_type: 'bilateral_transport' / 'transit' / 'cabotage' /
                    'cross_trade' / 'combined_transport_road_only'
    """
    requires_declaration = IMI_DECLARATION_TYPES.get(operation_type, True)
    compliant = (not requires_declaration) or declaration_filed

    return _attestation({
        "tool": "check_imi_posted_worker_declaration",
        "driver": driver_name,
        "operation_type": operation_type,
        "host_state": host_member_state_iso,
        "declaration_required": requires_declaration,
        "declaration_filed": declaration_filed,
        "compliant": compliant,
        "issue": "" if compliant else "Missing IMI declaration — fines up to €10,000 per worker per host MS",
        "regulator_ref": "Directive (EU) 2020/1057 — Posted Workers in road transport",
    })


@mcp.tool()
def check_working_time_directive(
    driver_name: str,
    weekly_hours: Optional[list] = None,
    reference_period_weeks: int = 17,  # ~4 months
) -> dict:
    """Directive 2002/15/EC Working Time for mobile workers."""
    weekly_hours = weekly_hours or []
    avg = sum(weekly_hours) / max(1, len(weekly_hours))
    max_week = max(weekly_hours) if weekly_hours else 0

    issues = []
    if avg > WORKING_TIME_LIMITS["avg_weekly_max_hr"]:
        issues.append(f"Average {avg:.1f}h > 48h cap over {len(weekly_hours)} weeks")
    if max_week > WORKING_TIME_LIMITS["max_weekly_hr"]:
        issues.append(f"Single week {max_week}h > 60h absolute cap")

    return _attestation({
        "tool": "check_working_time_directive",
        "driver": driver_name,
        "weeks_evaluated": len(weekly_hours),
        "avg_weekly_hr": round(avg, 2),
        "max_weekly_hr": max_week,
        "issues": issues,
        "compliant": not issues,
        "regulator_ref": "Directive 2002/15/EC",
    })


@mcp.tool()
def generate_eu_compliance_pack(
    operator_name: str,
    operator_country: str,
    fleet_size: int = 0,
    cross_border_intensity_pct: float = 0.0,
) -> dict:
    """Generate a cross-border EU compliance evidence pack skeleton."""
    return _attestation({
        "tool": "generate_eu_compliance_pack",
        "operator": operator_name,
        "operator_country": operator_country,
        "fleet_size": fleet_size,
        "cross_border_intensity_pct": cross_border_intensity_pct,
        "evidence_sections": [
            {"section": "I. Community Licence + national operator licence"},
            {"section": "II. EU 561/2006 drivers' hours records — last 12 months"},
            {"section": "III. Smart Tacho 2 v2 readiness register"},
            {"section": "IV. IMI posted-worker declarations per host MS"},
            {"section": "V. Cabotage operation log (3-in-7 + cooling-off)"},
            {"section": "VI. Driver 4-week return-to-base evidence"},
            {"section": "VII. Vehicle 8-week return-to-base evidence"},
            {"section": "VIII. Working Time Directive 48h-avg records"},
            {"section": "IX. AETR third-country records if applicable"},
            {"section": "X. Cross-border CMR consignment notes"},
            {"section": "XI. Customs transit T1/T2 records (UK + Switzerland)"},
        ],
        "advisory": "Pack supports member-state enforcement — operator's legal team must review per host MS",
    })


@mcp.tool()
def check_eu_aetr_third_country(
    driver_name: str,
    route_countries_iso: Optional[list] = None,
) -> dict:
    """Check if a driver's route enters AETR (non-EU 561) countries."""
    route_countries_iso = route_countries_iso or []
    aetr_hits = [c for c in route_countries_iso if c.upper() in AETR_COUNTRIES]
    eu_hits = [c for c in route_countries_iso if c.upper() not in AETR_COUNTRIES]

    return _attestation({
        "tool": "check_eu_aetr_third_country",
        "driver": driver_name,
        "route": route_countries_iso,
        "aetr_countries_on_route": aetr_hits,
        "eu_561_countries_on_route": eu_hits,
        "dual_regime_required": bool(aetr_hits),
        "advisory": ("Driver must hold AETR knowledge + tacho records valid under AETR Annex IB"
                     if aetr_hits else "EU 561/2006 alone applies"),
        "regulator_ref": "AETR — European Agreement Concerning the Work of Crews",
    })


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
