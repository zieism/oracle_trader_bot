# app/crud/__init__.py
from . import crud_trade
from . import crud_bot_settings # Add this line

# You can also expose specific functions if you prefer:
# from .crud_trade import create_trade, get_trade_by_id, ...
# from .crud_bot_settings import get_bot_settings, update_bot_settings