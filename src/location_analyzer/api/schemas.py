from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional

class PredictRequest(BaseModel):
    """Request schema for predicting location sales."""
    postcode: str = Field(..., description="The full UK postcode to analyze.")
    branch_name: Optional[str] = Field(None, description="Optional name of the branch.")

class PredictResponse(BaseModel):
    """Response schema returning the £ sales prediction and the features used."""
    postcode: str
    predicted_sales: float
    currency: str = "£"
    features: Dict[str, Any] = Field(..., description="The scraped/compiled features used by the ML model.")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "postcode": "SW1A 1AA",
                "predicted_sales": 1500.50,
                "currency": "£",
                "features": {
                    "population": 50000,
                    "avg_household_income": 45000
                }
            }
        }
    )
