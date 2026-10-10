import json
import math
import os
import tempfile
from typing import Any

import pandas as pd
import streamlit as st

from extractor import extract_text_from_file
from llm_client import extract_catalog_from_text
from matcher import match_to_master_catalog

TARGET_MET_STATUS = "🟢 Target Met"
TIGHT_MARGIN_STATUS = "🟡 Tight Margin"
LOW_MARGIN_STATUS = "🔴 Alert"
MISSING_VENDOR_PRICE_STATUS = "⚪ Missing vendor price"


def apply_pricing_rules(
    products: pd.DataFrame,
    vendor_discount_pct: float,
    target_margin_pct: float,
) -> pd.DataFrame:
    """Return product rows with company-side pricing and target-relative health."""
    priced = products.copy()
    vendor_prices = pd.to_numeric(priced["vendor_price"], errors="coerce")
    vendor_prices = vendor_prices.replace([math.inf, -math.inf], float("nan"))
    vendor_prices = vendor_prices.where(vendor_prices.gt(0))

    calculated_cost = vendor_prices * (1 - vendor_discount_pct / 100)
    dynamic_selling_price = calculated_cost / (1 - target_margin_pct / 100)
    projected_profit = dynamic_selling_price - calculated_cost
    achieved_margin = (projected_profit / dynamic_selling_price) * 100

    priced["vendor_price"] = vendor_prices
    priced["calculated_cost"] = calculated_cost
    priced["dynamic_selling_price"] = dynamic_selling_price
    priced["projected_profit"] = projected_profit
    priced["achieved_margin"] = achieved_margin
    priced["margin_status"] = MISSING_VENDOR_PRICE_STATUS
    margin_shortfall = target_margin_pct - achieved_margin
    epsilon = 1e-9
    priced.loc[margin_shortfall.le(epsilon), "margin_status"] = TARGET_MET_STATUS
    priced.loc[
        margin_shortfall.gt(epsilon) & margin_shortfall.le(5 + epsilon),
        "margin_status",
    ] = TIGHT_MARGIN_STATUS
    priced.loc[
        margin_shortfall.gt(5 + epsilon),
        "margin_status",
    ] = LOW_MARGIN_STATUS
    return priced


def render_pricing_kpis(container: Any, products: pd.DataFrame) -> None:
    valid_profits = products["projected_profit"].dropna()
    valid_selling_prices = products["dynamic_selling_price"].dropna()
    average_profit = valid_profits.mean() if not valid_profits.empty else None
    total_profit = products["projected_profit"].sum(min_count=1)
    total_selling_price = valid_selling_prices.sum()
    batch_margin = (
        total_profit / total_selling_price * 100
        if total_selling_price > 0 and pd.notna(total_profit)
        else None
    )

    with container.container():
        kpi_columns = st.columns(3)
        kpi_columns[0].metric("Total items extracted", f"{len(products):,}")
        kpi_columns[1].metric(
            "Average projected profit / unit",
            f"₹{average_profit:,.2f}" if average_profit is not None else "N/A",
            help="Average projected profit among items with a valid vendor price.",
        )
        kpi_columns[2].metric(
            "Estimated total batch margin",
            f"{batch_margin:.1f}%" if batch_margin is not None else "N/A",
            help="Total projected profit divided by total dynamic selling price.",
        )


st.set_page_config(
    page_title="Universal Catalog Sync",
    page_icon="📦",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

    :root {
        --ink: #172334;
        --muted: #738197;
        --line: #e8edf3;
        --surface: #ffffff;
        --canvas: #f5f7fb;
        --accent: #4b6bfb;
        --mint: #d9f6eb;
    }
    .stApp { background: var(--canvas); }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1380px; padding-top: 1.5rem; padding-bottom: 3rem; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
    h1, h2, h3 { font-family: 'Manrope', sans-serif; letter-spacing: -0.035em; }
    [data-testid="stSidebar"] { background: #fff; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] small {
        color: #26364a !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] label {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] h2 { color: #172334 !important; font-size: 1.05rem; }
    .hero {
        position: relative; overflow: hidden; padding: 2.2rem 2.4rem;
        border-radius: 24px; color: white;
        background: radial-gradient(circle at 82% 15%, #7e95ff 0, transparent 28%),
                    radial-gradient(circle at 93% 100%, #39c89a 0, transparent 32%),
                    linear-gradient(115deg, #15243b 0%, #243d65 58%, #315880 100%);
        box-shadow: 0 16px 40px rgba(27, 48, 80, .14);
    }
    .hero:after {
        content: ''; position: absolute; width: 240px; height: 240px; right: 8%;
        top: -145px; border: 1px solid rgba(255,255,255,.19); border-radius: 50%;
        box-shadow: 0 0 0 30px rgba(255,255,255,.035), 0 0 0 60px rgba(255,255,255,.025);
    }
    .hero-kicker { color: #c5d3ff; text-transform: uppercase; letter-spacing: .15em;
        font-size: .72rem; font-weight: 700; }
    .hero-title { color: #fff; font: 800 2.25rem/1.15 'Manrope', sans-serif;
        letter-spacing: -.05em; margin: .65rem 0 .55rem; }
    .hero-copy { color: #d7e0ef; font-size: 1rem; max-width: 680px; line-height: 1.6; }
    .hero-pill { display: inline-block; margin-top: 1rem; padding: .4rem .75rem;
        color: #e7fff5; background: rgba(88, 221, 170, .14); border: 1px solid rgba(151,255,211,.2);
        border-radius: 999px; font-size: .78rem; }
    .section-heading { margin: 1.6rem 0 .2rem; font-size: 1.25rem; font-weight: 750; }
    .section-caption { color: var(--muted); margin-bottom: .9rem; font-size: .91rem; }
    [data-testid="stMetric"] {
        background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
        padding: 1rem 1.2rem; box-shadow: 0 4px 14px rgba(31,48,74,.035);
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { font-family: 'Manrope', sans-serif; }
    [data-testid="stFileUploader"] {
        background: white; border: 1px dashed #cbd5e1; border-radius: 15px; padding: .45rem;
    }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border: 1px solid var(--line); border-radius: 15px; overflow: hidden;
    }
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 10px; font-weight: 700; min-height: 2.8rem;
    }
    div.stButton > button[kind="primary"] {
        color: white; border: 0; background: linear-gradient(100deg, #4969f5, #6a7df7);
        box-shadow: 0 7px 18px rgba(75,107,251,.2);
    }
    div.stButton > button[kind="primary"]:hover { color: white; border: 0; filter: brightness(1.05); }
    .empty-state { padding: 2rem; text-align: center; background: white;
        border: 1px solid var(--line); border-radius: 18px; color: var(--muted); }
    .photo-caption { color: var(--muted); font-size: .78rem; margin-top: .25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## ⚙️ Workspace")
    st.caption("Connect your product catalog and set company pricing.")
    master_catalog_file = st.file_uploader(
        "Master catalog",
        type=["csv"],
        help="A Name or SKU column is required. Image or URL columns are optional.",
    )
    match_threshold = 65
    st.divider()
    st.markdown("## ⚙️ Pricing & Margin Rules")
    target_margin_pct = st.slider(
        "Target Company Margin %",
        min_value=5,
        max_value=50,
        value=20,
        step=1,
        help="Target gross margin used to calculate the dynamic selling price.",
    )
    vendor_discount_pct = st.slider(
        "Negotiated Vendor Discount %",
        min_value=0,
        max_value=30,
        value=0,
        step=1,
        help="Discount applied to the single vendor-quoted price to estimate company cost.",
    )
    st.divider()
    st.caption("Supported source files")
    st.caption("PDF · PNG · JPG · WEBP · TIFF · BMP")

master_catalog = None
if master_catalog_file is not None:
    try:
        loaded_catalog = pd.read_csv(master_catalog_file)
        normalized_columns = {
            " ".join(str(column).replace("_", " ").casefold().split())
            for column in loaded_catalog.columns
        }
        if not normalized_columns.intersection(
            {"name", "product name", "item name", "sku", "master sku"}
        ):
            st.sidebar.error("Add a Name or SKU column to your master catalog CSV.")
        else:
            master_catalog = loaded_catalog
            st.sidebar.success(f"Catalog ready · {len(master_catalog):,} rows")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        st.sidebar.error(f"Could not read the master catalog CSV: {error}")

st.markdown(
    """
    <section class="hero">
      <div class="hero-kicker">Catalog operations workspace</div>
      <div class="hero-title">Universal Catalog Sync</div>
      <div class="hero-copy">Turn vendor menus into clean, review-ready product data.
      Extract from documents, match against your catalog, and export in one workflow.</div>
      <span class="hero-pill">✦ &nbsp; OCR · AI extraction · fuzzy matching</span>
    </section>
    """,
    unsafe_allow_html=True,
)

kpi_placeholder = st.empty()

st.markdown('<div class="section-heading">01 &nbsp; Add a vendor source</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-caption">Upload a PDF or a clear photo of the vendor menu or price list.</div>',
    unsafe_allow_html=True,
)
upload_column, preview_column = st.columns([1.15, 0.85], gap="large")
with upload_column:
    uploaded_file = st.file_uploader(
        "Choose a PDF or photo",
        type=["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
        label_visibility="collapsed",
        key="vendor_upload",
    )
    if uploaded_file is not None:
        st.caption(f"Selected: **{uploaded_file.name}** · {uploaded_file.size / 1024:.0f} KB")
    run_extraction = st.button(
        "✦  Extract and match products",
        type="primary",
        use_container_width=True,
        disabled=uploaded_file is None,
    )

with preview_column:
    if uploaded_file is not None:
        if uploaded_file.type and uploaded_file.type.startswith("image/"):
            st.image(
                uploaded_file.getvalue(),
                caption="Vendor source preview",
                use_container_width=True,
            )
        else:
            st.info("📄 PDF selected — its pages will be scanned during extraction.")
    else:
        st.markdown(
            '<div class="empty-state">📷<br><br><strong>Your source preview appears here</strong>'
            '<br>Menu photos and catalog thumbnails help make review easier.</div>',
            unsafe_allow_html=True,
        )

if run_extraction and uploaded_file is not None:
    with st.spinner("Reading the source and matching products…"):
        temp_path = ""
        try:
            file_ext = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                temp_path = tmp_file.name

            raw_text = extract_text_from_file(temp_path)
            llm_output = extract_catalog_from_text(raw_text)
            clean_data = json.loads(llm_output)
            products = clean_data.get("products", [])

            for product in products:
                match = match_to_master_catalog(
                    product["item_name"],
                    master_catalog,
                    threshold=match_threshold,
                )
                product["image_url"] = match["image_url"]
                product["matched_master_sku"] = match["matched_master_sku"]
                product["match_score"] = match["confidence"] / 100.0
                product["status"] = match["status"]

            columns = [
                "image_url",
                "status",
                "item_name",
                "matched_master_sku",
                "vendor_price",
                "calculated_cost",
                "dynamic_selling_price",
                "projected_profit",
                "achieved_margin",
                "margin_status",
                "match_score",
                "category",
                "seo_description",
            ]
            result = apply_pricing_rules(
                pd.DataFrame(products, columns=columns),
                vendor_discount_pct,
                target_margin_pct,
            )
            st.session_state["catalog_result"] = result
            st.session_state["catalog_source_name"] = uploaded_file.name
        except Exception as error:
            st.error(f"Processing failed: {error}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

if "catalog_result" in st.session_state:
    result = st.session_state["catalog_result"]
    if "vendor_price" not in result.columns:
        result["vendor_price"] = result["mrp"] if "mrp" in result.columns else float("nan")
    result = apply_pricing_rules(result, vendor_discount_pct, target_margin_pct)
    st.session_state["catalog_result"] = result
    render_pricing_kpis(kpi_placeholder, result)

    st.markdown('<div class="section-heading">02 &nbsp; Review your catalog</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-caption">Results from <strong>{st.session_state.get("catalog_source_name", "uploaded file")}</strong>. '
        "Edit any cell before exporting.</div>",
        unsafe_allow_html=True,
    )

    total_products = len(result)

    if total_products:
        with st.expander("Product photo preview", expanded=False):
            photo_rows = result[result["image_url"].fillna("").astype(str).str.strip().ne("")]
            if photo_rows.empty:
                st.caption("Add an Image or URL column to your master catalog CSV to show product photos.")
            else:
                photo_columns = st.columns(min(4, len(photo_rows)))
                for index, (_, product) in enumerate(photo_rows.head(8).iterrows()):
                    with photo_columns[index % len(photo_columns)]:
                        st.image(
                            product["image_url"],
                            caption=str(product["item_name"]),
                            use_container_width=True,
                        )

        filter_column, search_column = st.columns([0.75, 1.25])
        status_filter = filter_column.selectbox(
            "Show",
            [
                "All products",
                "Matched",
                "Needs review",
                "🟢 Target met",
                "🟡 Tight margin",
                "🔴 Low / unprofitable",
                "⚪ Missing vendor price",
            ],
        )
        search = search_column.text_input(
            "Search products",
            placeholder="Search item, category, SKU, or margin status",
        ).strip().casefold()
        visible = result.copy()
        if status_filter == "Matched":
            visible = visible[visible["status"].eq("✅ Mapped")]
        elif status_filter == "Needs review":
            visible = visible[~visible["status"].eq("✅ Mapped")]
        elif status_filter == "🟢 Target met":
            visible = visible[visible["margin_status"].eq(TARGET_MET_STATUS)]
        elif status_filter == "🟡 Tight margin":
            visible = visible[visible["margin_status"].eq(TIGHT_MARGIN_STATUS)]
        elif status_filter == "🔴 Low / unprofitable":
            visible = visible[visible["margin_status"].eq(LOW_MARGIN_STATUS)]
        elif status_filter == "⚪ Missing vendor price":
            visible = visible[visible["margin_status"].eq(MISSING_VENDOR_PRICE_STATUS)]
        if search:
            searchable = visible[
                ["item_name", "category", "matched_master_sku", "margin_status"]
            ].fillna("").astype(str).agg(" ".join, axis=1).str.casefold()
            visible = visible[searchable.str.contains(search, regex=False)]

        st.caption(f"Showing {len(visible):,} of {total_products:,} products")
        vendor_price_key = hash(
            tuple(
                None if pd.isna(price) else float(price)
                for price in pd.to_numeric(
                    visible["vendor_price"],
                    errors="coerce",
                )
            )
        )
        edited_df = st.data_editor(
            visible,
            column_config={
                "image_url": st.column_config.ImageColumn("Product photo", help="Image from your master catalog"),
                "status": st.column_config.SelectboxColumn("Match status", options=["✅ Mapped", "Unmapped", "Error"]),
                "item_name": "Vendor product",
                "matched_master_sku": "Matched master SKU",
                "vendor_price": st.column_config.NumberColumn(
                    "Vendor price",
                    format="₹%.2f",
                    help="Price quoted on the vendor document. Editing this recalculates company-side prices.",
                ),
                "calculated_cost": st.column_config.NumberColumn("Calculated cost", format="₹%.2f"),
                "dynamic_selling_price": st.column_config.NumberColumn("Dynamic selling price", format="₹%.2f"),
                "projected_profit": st.column_config.NumberColumn("Projected profit / unit", format="₹%.2f"),
                "achieved_margin": st.column_config.NumberColumn("Achieved margin", format="%.1f%%"),
                "margin_status": st.column_config.SelectboxColumn(
                    "Margin status",
                    options=[
                        TARGET_MET_STATUS,
                        TIGHT_MARGIN_STATUS,
                        LOW_MARGIN_STATUS,
                        MISSING_VENDOR_PRICE_STATUS,
                    ],
                ),
                "match_score": st.column_config.ProgressColumn("Confidence", min_value=0.0, max_value=1.0, format="%.0f%%"),
                "category": "Category",
                "seo_description": "Product description",
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            disabled=[
                "image_url",
                "status",
                "matched_master_sku",
                "calculated_cost",
                "dynamic_selling_price",
                "projected_profit",
                "achieved_margin",
                "margin_status",
                "match_score",
            ],
            key=(
                f"catalog_editor_{status_filter}_{search}_"
                f"{vendor_discount_pct}_{target_margin_pct}_{vendor_price_key}"
            ),
        )

        prices_before = tuple(
            None if pd.isna(price) else float(price)
            for price in pd.to_numeric(visible["vendor_price"], errors="coerce")
        )
        prices_after = tuple(
            None if pd.isna(price) else float(price)
            for price in pd.to_numeric(edited_df["vendor_price"], errors="coerce")
        )
        reviewed_df = apply_pricing_rules(
            edited_df,
            vendor_discount_pct,
            target_margin_pct,
        )
        updated_result = pd.concat(
            [
                result.drop(index=reviewed_df.index.intersection(result.index)),
                reviewed_df,
            ]
        ).sort_index()
        st.session_state["catalog_result"] = updated_result
        render_pricing_kpis(kpi_placeholder, updated_result)
        if prices_before != prices_after:
            st.rerun()

        download_column, json_download_column, note_column = st.columns([0.36, 0.34, 0.6])
        download_column.download_button(
            "↓  Download CSV",
            data=reviewed_df.to_csv(index=False).encode("utf-8"),
            file_name="universal_catalog_sync.csv",
            mime="text/csv",
            use_container_width=True,
        )
        json_download_column.download_button(
            "↓  Download JSON",
            data=reviewed_df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8"),
            file_name="universal_catalog_sync.json",
            mime="application/json",
            use_container_width=True,
        )
        note_column.caption("Exports include the rows currently shown by your filters.")
    else:
        st.info("No products were found in this source. Try a clearer image or another document.")
else:
    st.markdown(
        '<div class="section-heading">02 &nbsp; Your results</div>'
        '<div class="empty-state">Your extracted products and catalog matches will appear here.</div>',
        unsafe_allow_html=True,
    )
