# app/schemas/market_analysis.py
from pydantic import BaseModel
from typing import List, Dict, Any

class OHLCVWithIndicatorsAndRegime(BaseModel):
    market_regime: str  # وضعیت تشخیص داده شده بازار
    data: List[Dict[str, Any]] # لیست داده‌های کندل به همراه اندیکاتورها
