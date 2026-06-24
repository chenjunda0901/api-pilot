from pydantic import BaseModel
from typing import Optional


class CodeSnippetRequest(BaseModel):
    language: str  # curl, python, javascript, java, go, csharp
    environment_id: Optional[int] = None  # 指定环境用于解析模板变量


class CodeSnippetResponse(BaseModel):
    code: str
    language: str
