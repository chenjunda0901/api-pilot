from pydantic import BaseModel


class CodeSnippetRequest(BaseModel):
    language: str  # curl, python, javascript, java, go, csharp
    environment_id: int | None = None  # 指定环境用于解析模板变量


class CodeSnippetResponse(BaseModel):
    code: str
    language: str
