"""
===================================================================================
FILE: auth.py
ROLE: Authentication, JWT Security Token Engine & Role-Based Access Control (RBAC)
===================================================================================
WHAT THIS FILE CONTAINS:
- PBKDF2-HMAC-SHA256 password hashing and salt verification (Zero third-party dependency).
- RFC 7519 compliant HS256 JWT token encoding, decoding, and expiration validation.
- JSON-persisted multi-tenant user store (data/users.json) with auto-seeded default accounts.
- FastAPI dependency injection functions for HTTP Bearer authentication & RBAC authorization.
===================================================================================
"""
import os
import json
import time
import hmac
import hashlib
import base64
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import config

# FastAPI HTTPBearer security scheme (auto_error=False allows guest/anonymous fallback)
security_scheme = HTTPBearer(auto_error=False)

# Supported system roles
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_ANALYST = "analyst"
VALID_ROLES = {ROLE_ADMIN, ROLE_MANAGER, ROLE_ANALYST}


# =====================================================================
# 1. CRYPTOGRAPHIC PASSWORD HASHING (PBKDF2-HMAC-SHA256)
# =====================================================================
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Generates a secure PBKDF2-HMAC-SHA256 password hash string formatted as salt$hash."""
    if not salt:
        salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a salt$hash stored password string."""
    try:
        salt, _ = hashed_password.split('$', 1)
        expected_hash = hash_password(password, salt)
        return hmac.compare_digest(expected_hash, hashed_password)
    except Exception:
        return False


# =====================================================================
# 2. JWT TOKEN GENERATION & DECODING (HS256)
# =====================================================================
def _b64_encode(data: bytes) -> str:
    """Encodes bytes to unpadded URL-safe Base64 string."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _b64_decode(data_str: str) -> bytes:
    """Decodes unpadded URL-safe Base64 string to bytes."""
    padding = '=' * (4 - (len(data_str) % 4))
    return base64.urlsafe_b64encode(base64.urlsafe_b64decode((data_str + padding).encode('utf-8')))


def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """Creates a signed HS256 JWT access token string."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    if "sub" not in payload and "username" in payload:
        payload["sub"] = payload["username"]
    
    expire_seconds = expires_delta_seconds or (config.JWT_EXPIRE_MINUTES * 60)
    payload["exp"] = int(time.time()) + expire_seconds
    payload["iat"] = int(time.time())

    header_b64 = _b64_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _b64_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(
        config.JWT_SECRET_KEY.encode('utf-8'),
        signing_input,
        hashlib.sha256
    ).digest()
    
    sig_b64 = _b64_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates an HS256 JWT token. Raises HTTPException on invalid or expired token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Malformed token format")

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        
        expected_sig = hmac.new(
            config.JWT_SECRET_KEY.encode('utf-8'),
            signing_input,
            hashlib.sha256
        ).digest()
        
        actual_sig = base64.urlsafe_b64decode((sig_b64 + '=' * (4 - (len(sig_b64) % 4))).encode('utf-8'))
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid signature")

        payload_bytes = base64.urlsafe_b64decode((payload_b64 + '=' * (4 - (len(payload_b64) % 4))).encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))

        if "exp" in payload and time.time() > payload["exp"]:
            raise ValueError("Token has expired")

        return payload
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(ve)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =====================================================================
# 3. MULTI-TENANT USER STORE & AUTO-SEEDING
# =====================================================================
def get_users_db() -> Dict[str, Any]:
    """Loads users database from JSON file or seeds default accounts."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not config.USERS_REGISTRY_FILE.exists():
        default_users = {
            "admin": {
                "username": "admin",
                "full_name": "System Administrator",
                "email": "admin@fdic-rag.internal",
                "hashed_password": hash_password("admin123"),
                "role": ROLE_ADMIN,
                "company_id": "*",  # Super-admin access to all tenant workspaces
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "manager": {
                "username": "manager",
                "full_name": "FDIC Credit Risk Manager",
                "email": "manager@fdic-bank.com",
                "hashed_password": hash_password("manager123"),
                "role": ROLE_MANAGER,
                "company_id": config.DEFAULT_COMPANY_ID,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "analyst": {
                "username": "analyst",
                "full_name": "Credit Risk Analyst",
                "email": "analyst@fdic-bank.com",
                "hashed_password": hash_password("analyst123"),
                "role": ROLE_ANALYST,
                "company_id": config.DEFAULT_COMPANY_ID,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        save_users_db(default_users)
        return default_users

    try:
        with open(config.USERS_REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[User Store Read Error]: {e}")
        return {}


def save_users_db(users_db: Dict[str, Any]):
    """Saves updated users dictionary to JSON file."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.USERS_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(users_db, f, indent=2)


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates username and password against stored users database."""
    users = get_users_db()
    user = users.get(username.strip().lower())
    if not user:
        return None
    if verify_password(password, user["hashed_password"]):
        # Return user info without the hashed password
        return {
            "username": user["username"],
            "full_name": user.get("full_name", user["username"]),
            "email": user.get("email", ""),
            "role": user["role"],
            "company_id": user.get("company_id", config.DEFAULT_COMPANY_ID),
            "created_at": user.get("created_at", "")
        }
    return None


# =====================================================================
# 4. FASTAPI DEPENDENCY INJECTION & RBAC AUTHORIZATION
# =====================================================================
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency extracting current user from Bearer JWT header.
    Falls back to Guest user if no token is provided.
    """
    if not credentials or not credentials.credentials:
        # Anonymous Guest fallback user
        return {
            "username": "guest",
            "full_name": "Guest Visitor",
            "email": "guest@fdic-rag.internal",
            "role": ROLE_ANALYST,
            "company_id": config.DEFAULT_COMPANY_ID,
            "is_guest": True
        }

    token = credentials.credentials
    payload = decode_access_token(token)
    
    username = payload.get("sub") or payload.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"}
        )

    users = get_users_db()
    user = users.get(username)
    if not user:
        # Check payload user data directly if deleted from database
        return {
            "username": username,
            "full_name": payload.get("full_name", username),
            "email": payload.get("email", ""),
            "role": payload.get("role", ROLE_ANALYST),
            "company_id": payload.get("company_id", config.DEFAULT_COMPANY_ID),
            "is_guest": False
        }

    return {
        "username": user["username"],
        "full_name": user.get("full_name", user["username"]),
        "email": user.get("email", ""),
        "role": user["role"],
        "company_id": user.get("company_id", config.DEFAULT_COMPANY_ID),
        "is_guest": False
    }


def require_role(allowed_roles: List[str]):
    """Returns a dependency function enforcing that the user possesses one of the allowed roles."""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", ROLE_ANALYST)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Action requires one of roles: {', '.join(allowed_roles)}. Your role is '{user_role}'."
            )
        return current_user
    return role_checker


def verify_tenant_access(current_user: Dict[str, Any], target_company_id: str):
    """
    Enforces tenant access authorization.
    Admins (or users with company_id='*') can access any workspace.
    Managers/Analysts can only access their assigned company_id.
    """
    user_role = current_user.get("role", ROLE_ANALYST)
    user_cid = current_user.get("company_id", config.DEFAULT_COMPANY_ID)
    
    clean_target = config.sanitize_company_id(target_company_id)
    clean_user_cid = config.sanitize_company_id(user_cid)

    # Super-admin or '*' wildcard has access to all tenants
    if user_role == ROLE_ADMIN or user_cid == "*":
        return True

    # Allow guest users to query and explore any available workspace
    if current_user.get("is_guest"):
        return True

    if clean_user_cid != clean_target:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to tenant workspace '{clean_target}'. User '{current_user['username']}' is assigned to tenant '{clean_user_cid}'."
        )
    return True
