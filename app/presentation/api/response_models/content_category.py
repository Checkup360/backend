from pydantic import BaseModel, Field


class ContentCategoryResponse(BaseModel):
    key: str = Field(description="Stable health topic key used to tag content.")
    label: str = Field(description="Readable name of the health topic.")
    active: bool = Field(description="Whether the organization enabled the topic.")
