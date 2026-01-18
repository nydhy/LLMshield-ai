from pydantic import BaseModel, Field

class ShieldRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The user prompt to be scanned and processed")