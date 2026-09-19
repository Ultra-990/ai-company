"""Bounded response contract; validity does not prove the model's judgment."""
import json
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT = 'upwork-scope.v1'
INSTRUCTION = '''OUTPUT CONTRACT upwork-scope.v1 overrides prose formatting:
Return ONLY a JSON object with exactly these keys, in Polish:
{"fit":"SUPPORTED|CLARIFY|UNSUPPORTED","reason":"short explanation",
"questions":["question"],"scope":["deliverable"],
"acceptance_cases":["input -> expected output"],"exclusions":["not included"]}.
fit must be one of the three literal words, never their combined string.
reason <=600 characters. Each array <=5 strings of <=180 characters.
Whole JSON <=3200 characters. No Markdown, repetitions, code, extra sections
or claims about tests performed. For UNSUPPORTED, questions, scope and acceptance_cases
must all be empty: explain gaps in reason and exclusions. Do not negotiate away
mandatory requirements or ask whether explicitly mandatory features are optional.
For SUPPORTED, provide deliverables and test cases, and no unresolved questions.
If requirements are unclear use CLARIFY. Do not promise prices, deadlines,
contract acceptance or delivery. This is an opinion requiring owner review.'''

Item = Annotated[str, Field(min_length=1, max_length=180)]
Items = Annotated[list[Item], Field(max_length=5)]


class ScopeResult(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    fit: Literal['SUPPORTED','CLARIFY','UNSUPPORTED']
    reason: str = Field(min_length=10,max_length=600)
    questions: Items
    scope: Items
    acceptance_cases: Items
    exclusions: Items

    @model_validator(mode='after')
    def consistent(self):
        for values in (self.questions,self.scope,self.acceptance_cases,self.exclusions):
            if any(not v.strip() for v in values) or len(set(values)) != len(values):
                raise ValueError('Empty or repeated item')
        if self.fit=='SUPPORTED' and (self.questions or not self.scope or not self.acceptance_cases):
            raise ValueError('Supported scope requires deliverables, tests and no open questions')
        if self.fit=='UNSUPPORTED' and (self.questions or self.scope or self.acceptance_cases):
            raise ValueError('Unsupported scope must not propose executable deliverables')
        return self


def validate_result(content):
    if len(content)>3200 or '\x00' in content:
        raise ValueError('Scope response too long or invalid')
    def unique(pairs):
        data={}
        for key,value in pairs:
            if key in data:raise ValueError('Duplicate JSON key')
            data[key]=value
        return data
    ScopeResult.model_validate(json.loads(content,object_pairs_hook=unique))
