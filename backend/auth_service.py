"""
Authentication Service for Basant Jamini Bhawan Welfare Association Web App
Provides secure, standalone Admin authentication with session tokens.
Default credentials: admin / admin123
"""

import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
AUTH_FILE = os.path.join(DATA_DIR, "admin_auth.json")

class AuthManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.auth_data = self._load_auth()

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def _load_auth(self) -> Dict[str, Any]:
        if os.path.exists(AUTH_FILE):
            try:
                with open(AUTH_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default initialization: admin / admin123
        salt = secrets.token_hex(16)
        default_data = {
            "username": "admin",
            "salt": salt,
            "password_hash": self._hash_password("admin123", salt),
            "tokens": {}  # token -> expiry_iso
        }
        self._save_auth(default_data)
        return default_data

    def _save_auth(self, data: Dict[str, Any]):
        self.auth_data = data
        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def login(self, username: str, password: str) -> Optional[str]:
        """Validates credentials and returns a session token if valid."""
        stored_user = self.auth_data.get("username", "admin")
        if username.strip().lower() != stored_user.lower():
            return None

        salt = self.auth_data.get("salt", "")
        expected_hash = self.auth_data.get("password_hash", "")
        if self._hash_password(password, salt) != expected_hash:
            return None

        token = secrets.token_urlsafe(32)
        expiry = (datetime.now() + timedelta(days=7)).isoformat()
        
        # Cleanup expired tokens and store new token
        tokens = self.auth_data.get("tokens", {})
        now_iso = datetime.now().isoformat()
        clean_tokens = {t: exp for t, exp in tokens.items() if exp > now_iso}
        clean_tokens[token] = expiry
        self.auth_data["tokens"] = clean_tokens
        self._save_auth(self.auth_data)

        return token

    def is_valid_token(self, token: Optional[str]) -> bool:
        """Checks if a session token is valid and not expired."""
        if not token:
            return False
        tokens = self.auth_data.get("tokens", {})
        expiry = tokens.get(token)
        if not expiry:
            return False
        if datetime.now().isoformat() > expiry:
            del tokens[token]
            self._save_auth(self.auth_data)
            return False
        return True

    def logout(self, token: Optional[str]) -> bool:
        """Invalidates a session token."""
        if not token:
            return False
        tokens = self.auth_data.get("tokens", {})
        if token in tokens:
            del tokens[token]
            self._save_auth(self.auth_data)
            return True
        return False

    def change_password(self, old_password: str, new_password: str) -> (bool, str):
        """Allows changing the admin password if old password matches."""
        if len(new_password) < 4:
            return False, "New password must be at least 4 characters long."

        salt = self.auth_data.get("salt", "")
        expected_hash = self.auth_data.get("password_hash", "")
        if self._hash_password(old_password, salt) != expected_hash:
            return False, "Current password is incorrect."

        new_salt = secrets.token_hex(16)
        self.auth_data["salt"] = new_salt
        self.auth_data["password_hash"] = self._hash_password(new_password, new_salt)
        self.auth_data["tokens"] = {}  # Invalidate previous sessions
        self._save_auth(self.auth_data)
        return True, "Password successfully updated. Please log in with your new password."
