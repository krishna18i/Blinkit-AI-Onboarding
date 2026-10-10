import pytest
from pydantic import ValidationError
from parser import parse_and_validate_json

def test_parse_valid_json():
    raw_input = '{"products": [{"item_name": "Milk", "category": "Dairy", "vendor_price": 50, "seo_description": "Fresh milk"}]}'
    result = parse_and_validate_json(raw_input)
    assert len(result["products"]) == 1
    assert result["products"][0]["item_name"] == "Milk"
    assert result["products"][0]["vendor_price"] == 50
    assert "mrp" not in result["products"][0]

def test_parse_json_with_trailing_markdown():
    raw_input = 'Here is your data:\n```json\n{"products": [{"item_name": "Bread", "category": "Bakery", "vendor_price": 40, "seo_description": "Whole wheat"}]}\n```\nHope this helps!'
    result = parse_and_validate_json(raw_input)
    assert result["products"][0]["item_name"] == "Bread"

def test_parse_broken_json_missing_comma():
    raw_input = '{"products": [{"item_name": "Butter" "category": "Dairy" "vendor_price": 100 "seo_description": "Salted butter"}]}'
    result = parse_and_validate_json(raw_input)
    assert result["products"][0]["item_name"] == "Butter"

def test_parse_raw_product_list_and_ignore_extra_fields():
    raw_input = '[{"item_name": "Rice", "vendor_price": 80, "mrp": 85, "cost_price": 70, "discount": 5}]'
    result = parse_and_validate_json(raw_input)

    assert result["products"][0]["item_name"] == "Rice"
    assert result["products"][0]["vendor_price"] == 80
    assert result["products"][0]["category"] == "Uncategorized"
    assert result["products"][0]["seo_description"] == "No description available."
    assert "mrp" not in result["products"][0]
    assert "cost_price" not in result["products"][0]

def test_parse_missing_required_field_fails_validation():
    with pytest.raises(ValidationError):
        parse_and_validate_json('{"products": [{"item_name": "Rice"}]}')