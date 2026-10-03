import json

import dashboard_export as de


def test_parse_qa_report():
    text = "# R\n\n**Overall: PASS**\n\n## 1. Weekly dataset: PASS\n\n## 4. Forecast: FAIL\n"
    qa = de.parse_qa_report(text)
    assert qa["overall"] == "PASS"
    assert [(s["title"], s["status"]) for s in qa["sections"]] == [("Weekly dataset", "PASS"), ("Forecast", "FAIL")]


def test_payload_headline_comes_from_real_monthly_totals():
    payload = de.build_payload(".")
    k = payload["kpis"]
    assert k["electricity_kwh"] == 1059147 and k["diesel_litres"] == 4100
    assert k["electricity_tco2e"] == round(1059147 * 0.71 / 1000, 2)
    assert k["diesel_tco2e"] == round(4100 * 2.89 / 1000, 2)
    assert abs(k["covered_share_of_footprint"] - (k["covered_tco2e"] / 3719.74)) < 1e-3
    assert len(payload["real_monthly"]) == 12 and len(payload["weekly"]) == 52
    assert payload["meta"]["weekly_label"].startswith("SYNTHETIC")


def test_payload_is_json_serialisable_and_lists_all_factors():
    payload = de.build_payload(".")
    json.dumps(payload)
    assert {f["name"] for f in payload["factors"]} >= {"electricity", "diesel", "diesel_mobile"}
    assert all(f["source"] and f["version"] and f["unit"] for f in payload["factors"])


def test_payload_simulation_key():
    payload = de.build_payload(".")
    sim = payload["simulation"]
    # monthly baseline rows
    assert len(sim["baseline_monthly"]) == 12
    row0 = sim["baseline_monthly"][0]
    for col in ("month", "base_scope2_tco2e", "base_scope1_tco2e", "base_total_tco2e"):
        assert col in row0, f"Missing column: {col}"
    # factors cited
    names = {f["name"] for f in sim["factors_used"]}
    assert "electricity" in names and "diesel" in names
    # coverage note
    cn = sim["coverage_note"]
    assert cn["full_footprint_tco2e"] == 3719.74
    assert 19.0 < cn["covered_share_pct"] < 22.0
    # illustrative presets
    assert len(sim["presets"]) == 3
    for p in sim["presets"]:
        assert "ILLUSTRATIVE" in p["description"].upper()
        assert "saved_tco2e" in p["annual"]
    assert "ILLUSTRATIVE" in sim["presets_note"].upper()


def test_payload_solar_is_real_and_not_netted():
    payload = de.build_payload(".")
    s = payload["solar"]
    assert len(s["monthly"]) == 12
    assert s["annual_kwh"] == 21720  # Master Data sheet 6_Solar_Monthly, ANNUAL TOTAL
    assert s["annual_avoided_tco2e"] == round(21720 * 0.71 / 1000, 2)  # 15.42 in sheet 18_Scope_Summary
    assert s["period"] == "2025-03 to 2026-02"
    assert abs(s["share_of_purchased_electricity"] - 0.0205) < 0.001  # ~2.1 % per Master Data
    assert "NOT netted" in s["note"]
    # Scope 2 headline stays the purchased (billed) electricity
    assert payload["kpis"]["electricity_kwh"] == 1059147
