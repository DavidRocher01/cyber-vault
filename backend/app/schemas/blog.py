from pydantic import BaseModel, Field


class BlogPostOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    slug: str
    title: str
    description: str
    date: str
    readTime: int
    category: str
    tags: list[str]
    isPublished: bool


class BlogPostDetailOut(BlogPostOut):
    htmlContent: str


class BlogPostIn(BaseModel):
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    date: str = Field(min_length=1)
    readTime: int = Field(ge=1)
    category: str = Field(min_length=1)
    tags: list[str]
    htmlContent: str = Field(min_length=1)
    isPublished: bool = True
