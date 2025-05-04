from pydantic import BaseModel
from app.models.record_db import DNSRecord, RecordType
from typing import Union, List

class FlatRecord(BaseModel):
    type: str
    value: Union[str, dict, List[str]]


class GroupedRecordsResponse(BaseModel):
    hostname: str
    records: List[FlatRecord]

class DeleteDNSRecordInput(BaseModel):
    hostname: str
    type: RecordType
    value: Union[str, List[str]]