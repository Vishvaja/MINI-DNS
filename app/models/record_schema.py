from pydantic import BaseModel, Field, IPvAnyAddress, validator
from typing import List, Union, Literal
from typing import Annotated
from app.utils.hostname_utils import validate_hostname_or_raise,validate_non_empty_strings

class MXValue(BaseModel):
    priority: int
    host: str

    @validator("host")
    def validate_mx_host(cls, v):
        return validate_hostname_or_raise(v, "MX host")

# Record schemas classes
class ARecordSchema(BaseModel):
    hostname: str
    type: Literal["A"]
    value: List[IPvAnyAddress]
    ttl_seconds: int = Field(default=3600, ge=60)

class AAAARecordSchema(BaseModel):
    hostname: str
    type: Literal["AAAA"]
    value: List[IPvAnyAddress]
    ttl_seconds: int = Field(default=3600, ge=60)

class CNAMERecordSchema(BaseModel):
    hostname: str
    type: Literal["CNAME"]
    value: str
    ttl_seconds: int = Field(default=3600, ge=60)

    @validator("value")
    def validate_cname(cls, v):
        return validate_hostname_or_raise(v, "CNAME value")

class MXRecordSchema(BaseModel):
    hostname: str
    type: Literal["MX"]
    value: MXValue
    ttl_seconds: int = Field(default=3600, ge=60)

class TXTRecordSchema(BaseModel):
    hostname: str
    type: Literal["TXT"]
    value: List[str]
    ttl_seconds: int = Field(default=3600, ge=60)

    @validator("value")
    def validate_txt(cls, v):
        return validate_non_empty_strings(v)

DNSRecordInput = Annotated[
    Union[
        ARecordSchema,
        AAAARecordSchema,
        CNAMERecordSchema,
        MXRecordSchema,
        TXTRecordSchema,
    ],
    Field(discriminator="type")
]


