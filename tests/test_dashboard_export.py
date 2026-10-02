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
