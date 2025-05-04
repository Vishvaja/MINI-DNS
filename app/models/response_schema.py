from pydantic import BaseModel
from app.models.record_db import DNSRecord, RecordType
from typing import Union, List
from datetime import datetime

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

class DNSRecordResponse(BaseModel):
    hostname: str
    type: str
    value: Union[List[str], str, dict]
    timestamp_created: datetime
    ttl_seconds: int