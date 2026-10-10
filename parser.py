import re
import json
from json_repair import repair_json
from schemas import CatalogResponse

def parse_and_validate_json(raw_output: str) -> dict:
    match = re.search(r'\[.*\]|\{.*\}', raw_output, re.DOTALL)
    if not match:
        preview = raw_output[:250] + "..." if len(raw_output) > 250 else raw_output
        if not raw_output.strip():
            preview = "[Model returned a completely empty response]"
        raise ValueError(f"No JSON found. Model output: {preview}")

    repaired = repair_json(match.group(0))
    parsed_data = json.loads(repaired)
    if isinstance(parsed_data, list):
        parsed_data = {"products": parsed_data}
    elif not isinstance(parsed_data, dict):
        raise ValueError("Model output JSON must be a product list or an object")

    if "products" not in parsed_data:
        raise ValueError("Model output JSON object is missing the 'products' field")

    parsed_dict = parsed_data
    validated_data = CatalogResponse(**parsed_dict)
    return validated_data.model_dump()