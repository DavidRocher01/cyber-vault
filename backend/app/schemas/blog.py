from pydantic import BaseModel


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
    slug: str
    title: str
    description: str
    date: str
    readTime: int
    category: str
    tags: list[str]
    htmlContent: str
    isPublished: bool = True
