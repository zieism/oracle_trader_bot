# app/security/__init__.py
"""
Security module for Oracle Trader Bot

Contains authentication, authorization, and security utilities.
"""

from .admin_auth import admin_auth

__all__ = ["admin_auth"]
