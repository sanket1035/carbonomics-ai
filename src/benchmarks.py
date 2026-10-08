"""
benchmarks.py

Documented energy-performance benchmarks (EPI, kWh per m2 of built-up area per year) used by the
Energy Audit. Same rule as emission_factors.py: every value carries a source, a version and a unit,
and nothing is typed in anywhere else.

IMPORTANT - there is NO official BEE / ECBC EPI for educational buildings. The BEE Star Rating Scheme
covers offices, hotels, hospitals, malls and IT parks only. KKWIEER is a mostly naturally ventilated
campus with air-conditioning at 4 sites, so the nearest documented reference is the BEE office scheme
band for buildings with LESS THAN 50 % air-conditioned built-up area. CSE (2014) used the same office
scheme as an indicative comparison for educational buildings. Treat every value here as a PROXY.

Each entry has:
    value     - EPI, kWh/m2/year (for star bands this is the upper cut-off of the band)
    role      - "reference" (a rating band) or "aspirational" (net-zero label)
    verified  - False when part of the entry (here: which zone a column belongs to) is inferred from
                extracted PDF text and has NOT been checked against the original document.
"""

BENCHMARK_UNIT = "kWh/m2/year"

BEE_OFFICE_SOURCE = "BEE, Scheme for BEE Star Rating for Office Buildings (Annexure 3/4, EPI bands)"
BEE_OFFICE_VERSION = "February 2009"

# Climate zone of Nashik under NBC 2016 Part 11 is NOT confirmed (Composite vs Warm and Humid).
DEFAULT_ZONE = "composite"
ZONE_NOTE = ("Nashik's climate zone (Composite or Warm and Humid) is not confirmed. The 5-star cut-off "
             "is 40 (Composite) or 45 (Warm and Humid) kWh/m2/year; the audit conclusion is the same for both.")

# Upper bound of each star band, buildings with < 50 % air-conditioned built-up area.
# (1 star = highest EPI allowed; a building BELOW the 5-star cut-off earns 5 stars.)
# Column-to-zone mapping inferred from extracted PDF text -> verified=False.
BEE_OFFICE_LT50AC_BANDS = {
    "composite":    {"1": (70, 80), "2": (60, 70), "3": (50, 60), "4": (40, 50), "5": (None, 40)},
    "warm_humid":   {"1": (75, 85), "2": (65, 75), "3": (55, 65), "4": (45, 55), "5": (None, 45)},
    "hot_dry":      {"1": (65, 75), "2": (55, 65), "3": (45, 55), "4": (35, 45), "5": (None, 35)},
}

BENCHMARKS = {
    "bee_office_lt50ac_5star": {
        "label": "BEE 5-star cut-off, office scheme, <50% air-conditioned",
        "role": "reference",
        "unit": BENCHMARK_UNIT,
        "source": BEE_OFFICE_SOURCE,
        "version": BEE_OFFICE_VERSION,
        "basis": "Proxy: office scheme applied to an educational campus; the cut-off depends on the climate zone",
        "verified": False,
    },
    "shunya_net_zero": {
        "label": "BEE Shunya net-zero label (EPI 10 to 0)",
        "role": "aspirational",
        "value": 10.0,
        "unit": BENCHMARK_UNIT,
        "source": ("Net-Zero Energy Campuses in India, Sustainability 2024, 16(1), 87 "
                   "(secondary source quoting the BEE Shunya label)"),
        "version": "2024",
        "basis": "Aspirational only: how far the campus is from net-zero. Upper bound of the 10 to 0 range",
        "verified": False,
    },
}


def five_star_cutoff(zone: str = DEFAULT_ZONE) -> float:
    """EPI below which a <50 % air-conditioned building earns 5 stars (office scheme, proxy)."""
    return float(BEE_OFFICE_LT50AC_BANDS[zone]["5"][1])


def benchmark_value(key: str, zone: str = DEFAULT_ZONE) -> float:
    if key == "bee_office_lt50ac_5star":
        return five_star_cutoff(zone)
    return float(BENCHMARKS[key]["value"])


def star_rating(epi: float, zone: str = DEFAULT_ZONE) -> int:
    """Proxy star rating (1-5) for an EPI; 0 if the EPI is above the 1-star band."""
    bands = BEE_OFFICE_LT50AC_BANDS[zone]
    if epi < bands["5"][1]:
        return 5
    for star in ("4", "3", "2", "1"):
        low, high = bands[star]
        if low <= epi < high:
            return int(star)
    return 0


def benchmark_list(zone: str = DEFAULT_ZONE) -> list:
    """Documented benchmarks with their numeric value for the chosen zone (for the API / dashboard)."""
    out = []
    for key, spec in BENCHMARKS.items():
        item = {k: v for k, v in spec.items()}
        item["key"] = key
        item["value"] = benchmark_value(key, zone)
        out.append(item)
    return out
