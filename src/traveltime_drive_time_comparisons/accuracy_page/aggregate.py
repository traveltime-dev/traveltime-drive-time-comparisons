import json
import math
from typing import Dict, List, Optional, Set, Tuple

PROVIDERS = ["TravelTime", "TomTom", "HERE", "Mapbox", "Valhalla", "OSRM"]
REFERENCE_PROVIDER = "Google"
GOOGLE_COL = "google_travel_time"
CASE_COL = "case_category"
CLEAN = "clean"

PROVIDER_TRAVEL_TIME_COL = {
    "TravelTime": "tt_travel_time",
    "TomTom": "tomtom_travel_time",
    "HERE": "here_travel_time",
    "Mapbox": "mapbox_travel_time",
    "Valhalla": "valhalla_travel_time",
    "OSRM": "osrm_travel_time",
}

ACCURACY_BANDS = [
    (95.0, math.inf, "≥95%"),
    (90.0, 95.0, "90–95%"),
    (85.0, 90.0, "85–90%"),
    (80.0, 85.0, "80–85%"),
    (75.0, 80.0, "75–80%"),
    (-math.inf, 75.0, "<75%"),
]

TOD_SLOTS = ["05:00", "13:00", "17:00"]

DEFINITIONS = {
    "accuracy": "acc_P = 100 - |P_sec - Google_sec| / Google_sec * 100 over clean rows (P_sec===0 treated as no-result)",
    "signedError": "signed_err_P = (P_sec - Google_sec) / Google_sec * 100 (positive = over-predicts)",
    "rmse": "RMSE_P (seconds) = sqrt(mean((P_sec - Google_sec)^2)) over clean rows with both values present",
    "cleanFilter": 'case_category == "clean"',
    "bands": [label for _mn, _mx, label in ACCURACY_BANDS],
}

RUN_CSV_NAME = "output.csv"

AGGREGATE_FILES = {
    "headline": "headline.json",
    "bands": "bands.json",
    "time-of-day": "time-of-day.json",
    "bias": "bias.json",
    "by-state": "by-state.json",
    "meta": "meta.json",
}


def parse_number(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    s = raw.strip() if isinstance(raw, str) else raw
    if s == "" or s == "NaN":
        return None
    try:
        n = float(s)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def mean(xs: List[float]) -> float:
    if not xs:
        return math.nan
    return sum(xs) / len(xs)


def rmse_seconds(sec_errs: List[float]) -> float:
    if not sec_errs:
        return math.nan
    return math.sqrt(sum(v * v for v in sec_errs) / len(sec_errs))


def percentile(sorted_xs: List[float], q: float) -> float:
    n = len(sorted_xs)
    if n == 0:
        return math.nan
    if n == 1:
        return sorted_xs[0]
    pos = (n - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_xs[lo]
    w_hi = pos - lo
    return sorted_xs[lo] * (1 - w_hi) + sorted_xs[hi] * w_hi


def band_index(acc: float) -> int:
    for i, (mn, mx, _label) in enumerate(ACCURACY_BANDS):
        if acc >= mn and acc < mx:
            return i
    return len(ACCURACY_BANDS) - 1  # <75 catch-all


def extract_rows(
    subdivision_name: str, records: List[Dict[str, str]]
) -> Tuple[List[Dict], int, Set[str]]:
    by_key: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    for row in records:
        slot = (row.get("departure_time") or "")[11:16]
        by_key[(row.get("origin") or "", row.get("destination") or "", slot)] = row

    if not by_key:
        return [], 0, set()

    header = list(next(iter(by_key.values())).keys())
    present_providers = [
        (p, PROVIDER_TRAVEL_TIME_COL[p])
        for p in PROVIDERS
        if PROVIDER_TRAVEL_TIME_COL[p] in header
    ]

    rows: List[Dict] = []
    od_pairs: Set[str] = set()

    for (origin, destination, slot), row in by_key.items():
        od_pairs.add(f"{origin}|{destination}")
        is_clean = row.get(CASE_COL) == CLEAN

        google = parse_number(row.get(GOOGLE_COL)) if is_clean else None
        if google is None:
            continue

        provider_sec: Dict[str, Optional[float]] = {
            p: (parse_number(row.get(col)) if is_clean else None)
            for p, col in present_providers
        }
        rows.append(
            {
                "state": subdivision_name,
                "hour": slot,
                "google": google,
                "provider_sec": provider_sec,
            }
        )

    return rows, len(by_key), od_pairs


def aggregate(
    rows: List[Dict],
    slug: str,
    total_rows_scanned: int,
    total_od_pairs: int,
    generated_at: str,
    data_collected_at: str,
) -> Dict[str, object]:
    providers = [p for p in PROVIDERS if any(p in r["provider_sec"] for r in rows)]

    acc: Dict[str, List[float]] = {p: [] for p in PROVIDERS}
    signed: Dict[str, List[float]] = {p: [] for p in PROVIDERS}
    sec_err: Dict[str, List[float]] = {p: [] for p in PROVIDERS}
    clean_seen = {p: 0 for p in PROVIDERS}
    no_result = {p: 0 for p in PROVIDERS}
    tod: Dict[str, Dict[str, List[float]]] = {
        p: {"05:00": [], "13:00": [], "17:00": [], "overall": []} for p in PROVIDERS
    }
    by_state_acc: Dict[str, Dict[str, List[float]]] = {}
    google_seconds: List[float] = []

    for row in rows:
        g = row["google"]
        if g is not None and g > 0:
            google_seconds.append(g)
        state_bucket = by_state_acc.setdefault(row["state"], {})

        for p in providers:
            if p not in row["provider_sec"]:
                continue
            clean_seen[p] += 1
            ps = row["provider_sec"][p]
            if ps is None or ps == 0 or g is None or g == 0:
                no_result[p] += 1
                continue
            a = 100 - (abs(ps - g) / g) * 100
            s = ((ps - g) / g) * 100
            se = ps - g
            acc[p].append(a)
            signed[p].append(s)
            sec_err[p].append(se)
            tod[p]["overall"].append(a)
            if row["hour"] in TOD_SLOTS:
                tod[p][row["hour"]].append(a)
            state_bucket.setdefault(p, []).append(a)

    headline = []
    for p in providers:
        sorted_signed = sorted(signed[p])
        over = sum(1 for v in signed[p] if v > 0)
        headline.append(
            {
                "provider": p,
                "meanAccuracy": mean(acc[p]),
                "rmseSeconds": rmse_seconds(sec_err[p]),
                "medianBias": percentile(sorted_signed, 0.5),
                "shareOverPredicting": 0 if not signed[p] else over / len(signed[p]),
                "cleanRoutesScored": len(acc[p]),
            }
        )

    bands = []
    for p in providers:
        counts = [0] * len(ACCURACY_BANDS)
        for a in acc[p]:
            counts[band_index(a)] += 1
        total = clean_seen[p]
        bands.append(
            {
                "provider": p,
                "bands": [
                    {"label": label, "share": 0 if total == 0 else counts[i] / total}
                    for i, (_mn, _mx, label) in enumerate(ACCURACY_BANDS)
                ],
                "noResultShare": 0 if total == 0 else no_result[p] / total,
            }
        )

    time_of_day = [
        {
            "provider": p,
            "slots": {
                "05:00": mean(tod[p]["05:00"]),
                "13:00": mean(tod[p]["13:00"]),
                "17:00": mean(tod[p]["17:00"]),
                "overall": mean(tod[p]["overall"]),
            },
        }
        for p in providers
    ]

    bias = []
    for p in providers:
        s = sorted(signed[p])
        bias.append(
            {
                "provider": p,
                "p5": percentile(s, 0.05),
                "p25": percentile(s, 0.25),
                "median": percentile(s, 0.5),
                "p75": percentile(s, 0.75),
                "p95": percentile(s, 0.95),
                "min": s[0] if s else math.nan,
                "max": s[-1] if s else math.nan,
            }
        )

    by_state = []
    for state in sorted(by_state_acc.keys()):
        per: Dict[str, float] = {}
        for p in providers:
            arr = by_state_acc[state].get(p)
            if arr:
                per[p] = mean(arr)
        by_state.append({"state": state, "perProvider": per})

    meta = {
        "generatedAt": generated_at,
        "dataCollectedAt": data_collected_at,
        "totalRowsScanned": total_rows_scanned,
        "totalCleanRows": len(rows),
        "meanGoogleSeconds": mean(google_seconds),
        "totalOdPairs": total_od_pairs,
        "slug": slug,
        "providers": providers,
        "referenceProvider": REFERENCE_PROVIDER,
        "definitions": DEFINITIONS,
    }

    return {
        "headline": headline,
        "bands": bands,
        "time-of-day": time_of_day,
        "bias": bias,
        "by-state": by_state,
        "meta": meta,
    }


def _sanitize(obj):
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def dumps(payload) -> str:
    return json.dumps(_sanitize(payload), indent=2, ensure_ascii=False) + "\n"
