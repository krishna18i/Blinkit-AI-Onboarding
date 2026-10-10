import pandas as pd
from rapidfuzz import fuzz, process


def _normalize_column_name(column: object) -> str:
    return " ".join(str(column).replace("_", " ").casefold().split())


def _find_column(catalog: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    columns_by_name = {
        _normalize_column_name(column): str(column) for column in catalog.columns
    }
    return next(
        (
            columns_by_name[_normalize_column_name(name)]
            for name in candidates
            if _normalize_column_name(name) in columns_by_name
        ),
        None,
    )


def _unmapped_result() -> dict[str, str | float]:
    return {
        "matched_master_sku": "Unmapped",
        "image_url": "",
        "confidence": 0.0,
        "status": "Unmapped",
    }


def match_to_master_catalog(
    extracted_name: str,
    master_catalog: pd.DataFrame | None,
    threshold: int = 65,
) -> dict[str, str | float]:
    """Match a vendor product against an uploaded master catalog."""
    if master_catalog is None or master_catalog.empty:
        return _unmapped_result()

    name_column = _find_column(master_catalog, ("Name", "Product Name", "Item Name"))
    sku_column = _find_column(master_catalog, ("SKU", "Master SKU"))
    image_column = _find_column(master_catalog, ("Image", "URL", "Image URL"))
    match_column = name_column or sku_column
    if match_column is None:
        raise ValueError("Master catalog CSV must contain a Name or SKU column.")

    candidates = master_catalog[match_column].fillna("").astype(str).str.strip()
    valid_candidates = candidates[candidates.ne("")]
    if valid_candidates.empty:
        return _unmapped_result()

    match = process.extractOne(extracted_name, valid_candidates.tolist(), scorer=fuzz.WRatio)
    if match is None:
        return _unmapped_result()

    matched_value, score, row_position = match
    if score < threshold:
        result = _unmapped_result()
        result["confidence"] = round(score, 1)
        return result

    row = master_catalog.loc[valid_candidates.index[row_position]]
    matched_sku = row.get(sku_column, matched_value) if sku_column else matched_value
    image_url = row.get(image_column, "") if image_column else ""
    if pd.isna(matched_sku) or not str(matched_sku).strip():
        matched_sku = matched_value
    if pd.isna(image_url):
        image_url = ""

    return {
        "matched_master_sku": str(matched_sku).strip() or matched_value,
        "image_url": str(image_url).strip(),
        "confidence": round(score, 1),
        "status": "✅ Mapped",
    }