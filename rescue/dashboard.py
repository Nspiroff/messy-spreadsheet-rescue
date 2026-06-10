"""Interactive demo dashboard — run with:  streamlit run rescue/dashboard.py"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rescue.clean import rescue  # noqa: E402

st.set_page_config(page_title="Messy Spreadsheet Rescue", page_icon="🧹", layout="wide")


@st.cache_data
def load():
    messy = pd.read_csv(ROOT / "data" / "messy_sales.csv", dtype=str)
    clean, quarantined, log = rescue(ROOT / "data" / "messy_sales.csv")
    clean["order_date"] = pd.to_datetime(clean["order_date"])
    return messy, clean, quarantined, log


messy, clean, quarantined, log = load()

st.title("🧹 Messy Spreadsheet Rescue")
st.caption(
    "A live demo: 5,150 rows of realistically broken sales data go in — a clean "
    "dataset, a quantified rescue report, and this dashboard come out. "
    "[Source code on GitHub](https://github.com/Nspiroff/messy-spreadsheet-rescue)"
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Revenue recovered by cleaning", f"${log.revenue_recovered:,.0f}",
          help="Revenue invisible to a naive spreadsheet sum because prices were stored as text.")
m2.metric("Duplicate rows removed", f"{log.duplicate_rows_removed:,}")
m3.metric("Customer name variants merged", f"{log.customer_variants_merged:,}")
m4.metric("Rows quarantined for human review", f"{log.rows_quarantined:,}",
          help="Ambiguous rows are never silently guessed — they're flagged with a reason.")

tab_dash, tab_ba, tab_report = st.tabs(["📊 Dashboard", "🔍 Before / After", "📋 Rescue report"])

with tab_dash:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total revenue", f"${clean['revenue'].sum():,.0f}")
    k2.metric("Orders", f"{len(clean):,}")
    k3.metric("Customers", f"{clean['customer'].nunique():,}")
    k4.metric("Avg order value", f"${clean['revenue'].mean():,.2f}")

    monthly = (
        clean.set_index("order_date")["revenue"].resample("MS").sum().rename("Revenue")
    )
    st.subheader("Monthly revenue")
    st.line_chart(monthly, height=260)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top 10 customers")
        top = clean.groupby("customer")["revenue"].sum().nlargest(10).sort_values()
        st.bar_chart(top, horizontal=True, height=320)
    with c2:
        st.subheader("Revenue by category")
        bycat = clean.groupby("category")["revenue"].sum().sort_values()
        st.bar_chart(bycat, horizontal=True, height=320)

    st.subheader("Revenue by region")
    byregion = clean.groupby("region")["revenue"].sum().sort_values(ascending=False)
    st.dataframe(
        byregion.to_frame().style.format("${:,.0f}"),
        use_container_width=False,
    )

with tab_ba:
    st.markdown(
        "**The same spreadsheet, before and after.** Five date formats, prices as "
        "text, duplicate customers under different spellings — versus one tidy table."
    )
    show_cols = ["order_id", "order_date", "customer", "category", "quantity", "unit_price"]
    b, a = st.columns(2)
    with b:
        st.markdown("#### 🔴 Before — what the client sends")
        st.dataframe(messy[show_cols].head(15), height=560)
    with a:
        st.markdown("#### 🟢 After — what they get back")
        after = clean[show_cols + ["revenue"]].copy()
        after["order_date"] = after["order_date"].dt.date
        st.dataframe(after.head(15), height=560)

with tab_report:
    st.markdown(f"""
### Repairs, itemized — every number counted by the pipeline
- **{log.dates_normalized:,} dates normalized** from 5+ formats ({log.dates_excel_serial:,} were raw Excel serial numbers)
- **{log.money_values_parsed:,} prices parsed** out of currency text (`$1,234.56`, `1,234.56 USD`, …)
- **{log.decimal_shifts_fixed:,} decimal-shift typos fixed** (a $42 item entered as $4,200)
- **{log.customer_variants_merged:,} customer name variants merged** ({log.customers_before:,} raw spellings → {log.customers_after:,} real customers)
- **{log.categories_fixed:,} category labels repaired** · **{log.regions_normalized:,} regions standardized** · **{log.order_ids_relabeled:,} order IDs relabeled**
- **{log.cells_missing_standardized:,} fake-missing cells standardized** · **{log.cells_whitespace_trimmed:,} cells de-whitespaced**

### Quarantine — ambiguous rows get flagged, not guessed
""")
    st.dataframe(quarantined[["order_id", "customer", "product", "quantity", "unit_price", "reason"]].head(20))
    st.caption(
        f"{log.rows_quarantined:,} rows quarantined with reasons, so a human makes "
        "the judgment call — not the script. That's the difference between cleaning "
        "data and corrupting it."
    )
