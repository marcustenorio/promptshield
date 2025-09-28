# Enum com as ações do firewall
from enum import Enum

class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"

