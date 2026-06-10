"""Generate a realistically diseased small-business sales spreadsheet.

Every disease here is one I'd expect in a real client file: mixed date
formats, duplicate customers under name variants, currency stored as text,
missing values spelled six different ways, decimal-shift typos, and
re-entered (duplicate) orders.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .config import (
    CATEGORIES,
    DATE_END,
    DATE_START,
    MISSING_TOKENS,
    N_ORDERS,
    RATE_BLANK_DATE,
    RATE_DECIMAL_SHIFT,
    RATE_EXACT_DUPES,
    RATE_MISSING_CELLS,
    RATE_NEAR_DUPES,
    RATE_NEGATIVE_QTY,
    REGIONS,
    SEED,
)

CUSTOMER_BASES = [
    "Atlantic Supply", "Bayview Dental", "Chesapeake Motors", "Dominion Cafe",
    "Eastline Logistics", "First Colony Realty", "Greenbrier Gym", "Harbor Light Church",
    "Ironclad Fitness", "James River Tours", "Kettle & Crumb Bakery", "Landstown Pediatrics",
    "Mount Trashmore Mini Golf", "Norfolk Notary", "Oceanfront Surf Shop", "Pembroke Law Group",
    "Quality Crab Co", "Redwing Auto Parts", "Salem Lanes Bowling", "Tidewater Roofing",
    "Uptown Barbers", "Virginia Beach Vets", "Wavecrest Hotel", "Xpress Couriers",
    "Yorktown Catering", "Zenith HVAC", "Beacon Bookkeeping", "Cardinal Pest Control",
    "Driftwood Decor", "Emerald Cleaners", "Foxtail Florist", "Gull Point Marina",
    "Hilltop Hardware", "Inlet Ice Cream", "Jetty Joe's Tackle", "Kempsville Karate",
    "Lighthouse Daycare", "Marlin Print Shop", "Nansemond Nursery", "Osprey Optics",
]

CUSTOMER_SUFFIXES = ["", "", "", " Inc", ", Inc.", " LLC", " Co.", " Company"]

PRODUCTS = {
    "Electronics": ["Wireless Mouse", "USB-C Dock", "27in Monitor", "Label Printer"],
    "Office Supplies": ["Copy Paper Case", "Ink Cartridge", "Stapler Set", "Whiteboard"],
    "Furniture": ["Task Chair", "Standing Desk", "Bookshelf", "File Cabinet"],
    "Cleaning": ["Disinfectant 4-Pack", "Trash Liners Box", "Mop Kit", "Hand Soap Case"],
    "Food & Beverage": ["Coffee 5lb Bag", "Snack Variety Box", "Water Cooler Jug", "Tea Sampler"],
    "Safety Equipment": ["First Aid Kit", "Fire Extinguisher", "Safety Vest 10-Pack", "Wet Floor Signs"],
}

BASE_PRICES = {
    "Wireless Mouse": 24.99, "USB-C Dock": 89.0, "27in Monitor": 219.5, "Label Printer": 134.25,
    "Copy Paper Case": 42.0, "Ink Cartridge": 31.75, "Stapler Set": 18.5, "Whiteboard": 64.0,
    "Task Chair": 159.99, "Standing Desk": 389.0, "Bookshelf": 112.4, "File Cabinet": 98.75,
    "Disinfectant 4-Pack": 27.6, "Trash Liners Box": 22.99, "Mop Kit": 36.8, "Hand Soap Case": 29.4,
    "Coffee 5lb Bag": 48.25, "Snack Variety Box": 35.99, "Water Cooler Jug": 12.75, "Tea Sampler": 21.5,
    "First Aid Kit": 44.9, "Fire Extinguisher": 67.25, "Safety Vest 10-Pack": 52.0, "Wet Floor Signs": 19.99,
}

CATEGORY_TYPOS = {
    "Electronics": ["electronics", "ELECTRONICS", "Electroncs", "Electronics "],
    "Office Supplies": ["office supplies", "Office supplies", "Ofice Supplies", "OFFICE SUPPLIES"],
    "Furniture": ["furniture", "Furnture", "FURNITURE", " Furniture"],
    "Cleaning": ["cleaning", "CLEANING", "Cleening", "Cleaning  "],
    "Food & Beverage": ["food & beverage", "Food and Beverage", "F&B", "FOOD & BEVERAGE"],
    "Safety Equipment": ["safety equipment", "Safety Eqipment", "SAFETY EQUIPMENT", "Safety equip."],
}

REGION_VARIANTS = {
    "VA": ["VA", "va", "Virginia", "VA ", "virginia"],
    "NC": ["NC", "nc", "North Carolina", " NC"],
    "MD": ["MD", "Maryland", "md"],
    "DC": ["DC", "D.C.", "Washington DC", "dc"],
    "SC": ["SC", "South Carolina", "sc "],
}


def _date_pool() -> list[date]:
    start = date.fromisoformat(DATE_START)
    end = date.fromisoformat(DATE_END)
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _mangle_date(rng: random.Random, d: date) -> str:
    style = rng.randrange(6)
    if style == 0:
        return d.isoformat()                          # 2026-03-14
    if style == 1:
        return f"{d.month}/{d.day}/{d.year}"          # 3/14/2026
    if style == 2:
        return d.strftime("%d-%b-%y")                 # 14-Mar-26
    if style == 3:
        return d.strftime("%B %d, %Y")                # March 14, 2026
    if style == 4:
        return d.strftime("%m/%d/%y")                 # 03/14/26
    # Excel serial number (days since 1899-12-30)
    return str((d - date(1899, 12, 30)).days)


def _mangle_money(rng: random.Random, x: float) -> str:
    style = rng.randrange(4)
    if style == 0:
        return f"{x:.2f}"
    if style == 1:
        return f"${x:,.2f}"
    if style == 2:
        return f"{x:,.2f} USD"
    return f"$ {x:.2f}"


def _mangle_customer(rng: random.Random, base: str) -> str:
    name = base + rng.choice(CUSTOMER_SUFFIXES)
    style = rng.randrange(5)
    if style == 0:
        name = name.upper()
    elif style == 1:
        name = name.lower()
    if rng.random() < 0.15:
        name = name.replace(" ", "  ", 1)
    if rng.random() < 0.2:
        name = name + " "
    return name


def build_messy(out_csv: str | Path) -> pd.DataFrame:
    rng = random.Random(SEED)
    dates = _date_pool()
    rows = []
    for i in range(N_ORDERS):
        category = rng.choice(CATEGORIES)
        product = rng.choice(PRODUCTS[category])
        base_price = BASE_PRICES[product]
        price = round(base_price * rng.uniform(0.95, 1.08), 2)
        qty: object = rng.choice([1, 1, 1, 2, 2, 3, 4, 5, 8, 10])
        d = rng.choice(dates)
        base_cust = rng.choice(CUSTOMER_BASES)
        region_key = rng.choice(REGIONS)

        # diseases ---------------------------------------------------------
        if rng.random() < RATE_DECIMAL_SHIFT:
            price = round(price * 100, 2)             # decimal-shift typo
        if rng.random() < RATE_NEGATIVE_QTY:
            qty = -qty                                 # return entered as negative
        if rng.random() < 0.04:
            qty = float(qty)                           # 2.0 instead of 2
        if rng.random() < 0.005:
            qty = rng.choice(MISSING_TOKENS[1:5])      # unusable quantity

        date_str = "" if rng.random() < RATE_BLANK_DATE else _mangle_date(rng, d)
        cat_str = rng.choice([category] + CATEGORY_TYPOS[category]) if rng.random() < 0.5 else category
        region = rng.choice(REGION_VARIANTS[region_key])
        if rng.random() < RATE_MISSING_CELLS:
            region = rng.choice(MISSING_TOKENS)

        oid_style = rng.random()
        if oid_style < 0.9:
            oid = f"ORD-{10000 + i}"
        elif oid_style < 0.97:
            oid = f"ord {10000 + i}"
        else:
            oid = ""

        rows.append({
            "order_id": oid,
            "order_date": date_str,
            "customer": _mangle_customer(rng, base_cust),
            "region": region,
            "category": cat_str,
            "product": product,
            "quantity": qty,
            "unit_price": _mangle_money(rng, price),
        })

    df = pd.DataFrame(rows)

    # exact duplicate rows (the same order pasted twice)
    n_exact = int(N_ORDERS * RATE_EXACT_DUPES)
    dupes = df.sample(n=n_exact, random_state=SEED)
    # near-duplicates: same order re-entered with a different date format
    n_near = int(N_ORDERS * RATE_NEAR_DUPES)
    near = df.sample(n=n_near, random_state=SEED + 1).copy()
    near["order_date"] = [
        _mangle_date(random.Random(SEED + 2 + i), rng.choice(dates)) for i in range(len(near))
    ]

    df = pd.concat([df, dupes, near], ignore_index=True)
    df = df.sample(frac=1, random_state=SEED + 3).reset_index(drop=True)

    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    return df


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "messy_sales.csv"
    df = build_messy(out)
    print(f"wrote {len(df)} rows -> {out}")
