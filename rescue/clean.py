"""The rescue pipeline: messy sales CSV in, clean dataset + quantified report out.

Design rules:
- every fix is COUNTED so the client sees exactly what changed
- anything ambiguous is QUARANTINED for human review, never silently guessed
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from .config import CATEGORIES, MISSING_TOKENS

EXCEL_EPOCH = date(1899, 12, 30)
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%y", "%B %d, %Y", "%m/%d/%y"]
LEGAL_SUFFIXES = re.compile(r"\b(incorporated|inc|llc|co|corp|company|ltd)\b\.?,?", re.I)

REGION_MAP = {
    "va": "VA", "virginia": "VA",
    "nc": "NC", "north carolina": "NC",
    "md": "MD", "maryland": "MD",
    "dc": "DC", "d.c.": "DC", "washington dc": "DC",
    "sc": "SC", "south carolina": "SC",
}


@dataclass
class RescueLog:
    """Counts of every repair, for the client-facing report."""

    cells_whitespace_trimmed: int = 0
    cells_missing_standardized: int = 0
    dates_normalized: int = 0
    dates_excel_serial: int = 0
    money_values_parsed: int = 0
    quantities_parsed: int = 0
    decimal_shifts_fixed: int = 0
    categories_fixed: int = 0
    regions_normalized: int = 0
    customer_variants_merged: int = 0
    customers_before: int = 0
    customers_after: int = 0
    order_ids_relabeled: int = 0
    duplicate_rows_removed: int = 0
    rows_quarantined: int = 0
    quarantine_reasons: dict = field(default_factory=dict)
    rows_in: int = 0
    rows_out: int = 0
    naive_revenue: float = 0.0
    clean_revenue: float = 0.0

    @property
    def revenue_recovered(self) -> float:
        return self.clean_revenue - self.naive_revenue


def _naive_revenue(df: pd.DataFrame) -> float:
    """What a straight pandas read of the messy file can see: only rows where
    quantity and unit_price already parse as plain numbers."""
    qty = pd.to_numeric(df["quantity"], errors="coerce")
    price = pd.to_numeric(df["unit_price"], errors="coerce")
    rev = (qty * price).where(qty > 0)
    return float(rev.sum(skipna=True))


def _is_texty(series: pd.Series) -> bool:
    return pd.api.types.is_string_dtype(series) or series.dtype == object


def _strip_whitespace(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    for col in df.columns:
        if _is_texty(df[col]):
            before = df[col].astype("string")
            after = before.str.strip().str.replace(r"\s{2,}", " ", regex=True)
            changed = (before != after) & before.notna()
            log.cells_whitespace_trimmed += int(changed.sum())
            df[col] = after
    return df


def _standardize_missing(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    tokens = {t.strip().lower() for t in MISSING_TOKENS}
    for col in df.columns:
        if _is_texty(df[col]):
            s = df[col].astype("string")
            mask = s.str.strip().str.lower().isin(tokens) & s.notna()
            log.cells_missing_standardized += int(mask.sum())
            df[col] = s.mask(mask)
    return df


def _parse_one_date(value: object) -> tuple[pd.Timestamp | None, bool]:
    """Returns (timestamp, was_excel_serial)."""
    if pd.isna(value):
        return None, False
    s = str(value).strip()
    if s.isdigit() and 30000 < int(s) < 60000:          # Excel serial range ~1982-2064
        return pd.Timestamp(EXCEL_EPOCH + timedelta(days=int(s))), True
    for fmt in DATE_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(s, fmt)), False
        except ValueError:
            continue
    return None, False


def _parse_dates(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    parsed, serials = [], 0
    for v in df["order_date"]:
        ts, was_serial = _parse_one_date(v)
        parsed.append(ts)
        serials += was_serial
    df["order_date"] = parsed
    log.dates_normalized = int(pd.Series(parsed).notna().sum())
    log.dates_excel_serial = serials
    return df


def _parse_money(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    raw = df["unit_price"].astype("string")
    cleaned = (
        raw.str.replace(r"(?i)usd", "", regex=True)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["unit_price"] = pd.to_numeric(cleaned, errors="coerce")
    log.money_values_parsed = int(df["unit_price"].notna().sum())
    return df


def _parse_quantity(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    log.quantities_parsed = int(df["quantity"].notna().sum())
    return df


def _fix_decimal_shift(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    """A price 100x its product's median is a data-entry decimal slip."""
    median = df.groupby("product")["unit_price"].transform("median")
    shifted = df["unit_price"].notna() & (df["unit_price"] > 20 * median)
    plausible = (df["unit_price"] / 100).between(0.5 * median, 1.5 * median)
    fix = shifted & plausible
    df.loc[fix, "unit_price"] = df.loc[fix, "unit_price"] / 100
    log.decimal_shifts_fixed = int(fix.sum())
    return df


def _canon_customer_key(name: str) -> str:
    s = LEGAL_SUFFIXES.sub("", name.lower())
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _merge_customers(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    names = df["customer"].dropna()
    log.customers_before = int(names.nunique())
    keys = names.map(_canon_customer_key)
    # display name per key = most common Title Case spelling of the base name
    display = (
        pd.DataFrame({"key": keys, "name": keys.str.title()})
        .groupby("key")["name"]
        .agg(lambda s: s.mode().iat[0])
    )
    for wrong, right in {"Hvac": "HVAC", "Ems": "EMS", "Llc": "LLC"}.items():
        display = display.str.replace(rf"\b{wrong}\b", right, regex=True)
    df["customer"] = keys.map(display)
    log.customers_after = int(df["customer"].dropna().nunique())
    log.customer_variants_merged = log.customers_before - log.customers_after
    return df


def _fix_categories(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    canon = {c.lower(): c for c in CATEGORIES}
    extra = {"f&b": "Food & Beverage", "food and beverage": "Food & Beverage",
             "safety equip.": "Safety Equipment"}

    def fix(value: object) -> object:
        if pd.isna(value):
            return value
        s = str(value).strip().lower()
        if s in canon:
            return canon[s]
        if s in extra:
            return extra[s]
        match = difflib.get_close_matches(s, list(canon), n=1, cutoff=0.75)
        return canon[match[0]] if match else value

    before = df["category"].copy()
    df["category"] = df["category"].map(fix)
    log.categories_fixed = int((before != df["category"]).sum())
    return df


def _fix_regions(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    def fix(value: object) -> object:
        if pd.isna(value):
            return value
        return REGION_MAP.get(str(value).strip().lower(), value)

    before = df["region"].copy()
    df["region"] = df["region"].map(fix)
    changed = (before != df["region"]) & before.notna()
    log.regions_normalized = int(changed.sum())
    return df


def _fix_order_ids(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    s = df["order_id"].astype("string")
    fixed = s.str.upper().str.replace(r"^ORD[\s_]+", "ORD-", regex=True)
    changed = (s != fixed) & s.notna()
    log.order_ids_relabeled = int(changed.sum())
    df["order_id"] = fixed
    return df


def _dedupe(df: pd.DataFrame, log: RescueLog) -> pd.DataFrame:
    n0 = len(df)
    df = df.drop_duplicates()
    # near-dupes: same order re-entered with a different date
    key = ["order_id", "customer", "product", "quantity", "unit_price"]
    has_id = df["order_id"].notna()
    df = pd.concat([
        df[has_id].drop_duplicates(subset=key, keep="first"),
        df[~has_id],
    ]).sort_index()
    log.duplicate_rows_removed = n0 - len(df)
    return df


def _quarantine(df: pd.DataFrame, log: RescueLog) -> tuple[pd.DataFrame, pd.DataFrame]:
    reasons = pd.Series("", index=df.index, dtype="string")
    reasons[df["order_date"].isna()] += "unparseable or missing date; "
    reasons[df["unit_price"].isna()] += "unparseable price; "
    reasons[df["quantity"].isna()] += "unparseable quantity; "
    reasons[df["quantity"] < 0] += "negative quantity (possible return) - needs human review; "
    bad = reasons.str.len() > 0
    quarantined = df[bad].assign(reason=reasons[bad].str.rstrip("; "))
    log.rows_quarantined = int(bad.sum())
    log.quarantine_reasons = (
        quarantined["reason"].value_counts().to_dict() if len(quarantined) else {}
    )
    return df[~bad].copy(), quarantined


def rescue(messy_csv: str | Path, out_dir: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, RescueLog]:
    """Run the full pipeline. Returns (clean_df, quarantine_df, log)."""
    messy_csv = Path(messy_csv)
    raw = pd.read_csv(messy_csv, dtype=str)
    log = RescueLog(rows_in=len(raw))
    log.naive_revenue = _naive_revenue(raw)

    df = raw.copy()
    df = _strip_whitespace(df, log)
    df = _standardize_missing(df, log)
    df = _parse_dates(df, log)
    df = _parse_money(df, log)
    df = _parse_quantity(df, log)
    df = _fix_decimal_shift(df, log)
    df = _merge_customers(df, log)
    df = _fix_categories(df, log)
    df = _fix_regions(df, log)
    df = _fix_order_ids(df, log)
    df = _dedupe(df, log)
    df, quarantined = _quarantine(df, log)

    df["revenue"] = df["quantity"] * df["unit_price"]
    log.rows_out = len(df)
    log.clean_revenue = float(df["revenue"].sum())

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "clean_sales.csv", index=False)
        quarantined.to_csv(out_dir / "quarantine.csv", index=False)
    return df, quarantined, log
