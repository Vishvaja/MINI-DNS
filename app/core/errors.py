from fastapi import HTTPException

class ErrorCode:
    INVALID_HOSTNAME = "Invalid hostname format"
    DUPLICATE_RECORD = "Duplicate record already exists"
    CONFLICT_CNAME_EXISTS = "CNAME already exists for this hostname"
    CONFLICT_A_EXISTS = "A/AAAA records already exist for this hostname"
    CNAME_LOOP = "CNAME loop detected"
    CNAME_DEPTH_EXCEEDED = "CNAME chaining exceeds allowed depth"
    RECORD_NOT_FOUND = "Record not found for this hostname"

def raise_error(detail: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=detail)
