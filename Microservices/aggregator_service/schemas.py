from pydantic import BaseModel, Field

class AggregateRequest(BaseModel):
    stay_id: str = Field(..., description="The ID of the visit/stay to aggregate")

class AggregateResponse(BaseModel):
    stay_id: str
    aggregated_files: int
    modified_windows: list[int]
    errors: list[str] = Field(default_factory=list)
