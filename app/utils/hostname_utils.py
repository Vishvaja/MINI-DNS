# app/utils/validation_utils.py
import re
from typing import List, Union, Literal
import logging

logger = logging.getLogger(__name__)

def is_regex_hostname(hostname: str) -> bool:
    """
    Validates full hostnames including subdomains (e.g., abc.z.com, mail.example.co.uk)
    """
    if len(hostname) > 253:
        return False

    pattern = r"^(?=.{1,253}$)(?!-)[A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?(?:\.(?!-)[A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)*$"
    return re.match(pattern, hostname) is not None

def validate_hostname_or_raise(v: str, field_name: str = "value") -> str:
    ip_pattern = r"^\d{1,3}(\.\d{1,3}){3}$"
    if re.match(ip_pattern, v):
        raise ValueError(f"{field_name} must be a hostname, not an IP address")
    return v

def validate_non_empty_strings(lst: List[str]) -> List[str]:
    if not lst:
        raise ValueError("List cannot be empty")
    for s in lst:
        if not isinstance(s, str) or not s.strip():
            raise ValueError("Each entry must be a non-empty string")
    return lst
