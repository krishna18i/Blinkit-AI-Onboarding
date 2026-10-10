from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

class ProductItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item_name: str = Field(..., description="Full product name, including brand and variant")
    vendor_price: float = Field(
        ...,
        description="Single price explicitly quoted by the vendor",
    )
    category: Optional[str] = Field(
        default="Uncategorized",
        description="Product category",
    )
    seo_description: Optional[str] = Field(
        default="No description available.",
        description="Two-sentence product summary",
    )

class CatalogResponse(BaseModel):
    products: list[ProductItem]