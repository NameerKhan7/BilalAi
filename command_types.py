"""Small, validated set of requests the local assistant can execute."""
from dataclasses import dataclass
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator

class CommandDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action: Literal['open_browser','open_site','web_search']
    site: Literal['google','youtube','wikipedia']='google'
    query: str=Field(default='',max_length=400)

    @model_validator(mode='after')
    def check_required_fields(self):
        self.query=self.query.strip()
        if self.action=='web_search' and not self.query:
            raise ValueError('A search needs query words.')
        return self

@dataclass(frozen=True)
class RequestResult:
    reply: str
    kind: str
    url: str | None=None
