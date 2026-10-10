import pandas as pd

from matcher import match_to_master_catalog


def test_matches_name_and_returns_sku_and_image():
    catalog = pd.DataFrame(
        [
            {"Name": "Mango Juice 1L", "SKU": "DRINK-001", "Image": "https://example.test/mango.png"},
            {"Name": "Apple Juice 1L", "SKU": "DRINK-002", "Image": ""},
        ]
    )

    result = match_to_master_catalog("Mango Juice", catalog)

    assert result["matched_master_sku"] == "DRINK-001"
    assert result["image_url"] == "https://example.test/mango.png"
    assert result["status"] == "✅ Mapped"
    assert result["confidence"] >= 65


def test_matches_sku_when_name_column_is_missing():
    catalog = pd.DataFrame([{"SKU": "DRINK-001", "URL": "https://example.test/mango.png"}])

    result = match_to_master_catalog("DRINK-001", catalog)

    assert result["matched_master_sku"] == "DRINK-001"
    assert result["image_url"] == "https://example.test/mango.png"
    assert result["status"] == "✅ Mapped"


def test_no_catalog_returns_unmapped():
    result = match_to_master_catalog("Mango Juice", None)

    assert result == {
        "matched_master_sku": "Unmapped",
        "image_url": "",
        "confidence": 0.0,
        "status": "Unmapped",
    }
