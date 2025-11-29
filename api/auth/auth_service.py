"""
Auth Service - Authentication and authorization management
Handles user authentication, token management, and access control
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import jwt

from utils.trace_logger import trace, trace_async_calls
from config.settings import settings


class User:
    """User model"""

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        password_hash: str,
        roles: List[str] = None
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.roles = roles or ["user"]
        self.created_at = datetime.now()
        self.last_login = None
        self.is_active = True


class AuthToken:
    """Authentication token"""

    def __init__(self, token: str, user_id: str, expires_at: datetime):
        self.token = token
        self.user_id = user_id
        self.created_at = datetime.now()
        self.expires_at = expires_at
        self.is_valid = True


class AuthService:
    """
    Authentication and authorization service
    All auth operations are traced to files for security audit
    """

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.tokens: Dict[str, AuthToken] = {}
        self.api_keys: Dict[str, str] = {}  # api_key -> user_id

        # Initialize with demo user
        self._create_demo_user()

        trace.info("AuthService initialized", module=__name__, function="__init__")

    def _create_demo_user(self):
        """Create a demo user for testing"""
        demo_user = User(
            user_id="demo_user_001",
            username="demo",
            email="demo@daypilot.com",
            password_hash=self._hash_password("demo123"),
            roles=["user", "admin"]
        )
        self.users[demo_user.user_id] = demo_user

        # Create demo API key
        demo_api_key = "demo_api_key_" + secrets.token_hex(16)
        self.api_keys[demo_api_key] = demo_user.user_id

        trace.info(
            "Demo user created",
            context={
                "user_id": demo_user.user_id,
                "username": demo_user.username,
                "api_key": demo_api_key
            },
            module=__name__,
            function="_create_demo_user"
        )

    def _hash_password(self, password: str) -> str:
        """Hash password with SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    @trace_async_calls
    async def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate user with username and password
        Returns access token if successful
        """

        trace.info(
            f"Authentication attempt for user: {username}",
            context={"username": username},
            module=__name__,
            function="authenticate"
        )

        # Find user
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break

        if not user:
            trace.warning(
                f"Authentication failed: user not found: {username}",
                module=__name__,
                function="authenticate"
            )
            return None

        # Verify password
        password_hash = self._hash_password(password)
        if password_hash != user.password_hash:
            trace.warning(
                f"Authentication failed: invalid password for user: {username}",
                context={"user_id": user.user_id},
                module=__name__,
                function="authenticate"
            )
            return None

        # Check if user is active
        if not user.is_active:
            trace.warning(
                f"Authentication failed: user inactive: {username}",
                context={"user_id": user.user_id},
                module=__name__,
                function="authenticate"
            )
            return None

        # Generate token
        token = await self.create_token(user.user_id)

        # Update last login
        user.last_login = datetime.now()

        trace.info(
            f"Authentication successful for user: {username}",
            context={
                "user_id": user.user_id,
                "username": username
            },
            module=__name__,
            function="authenticate"
        )

        return token

    @trace_async_calls
    async def create_token(self, user_id: str) -> str:
        """Create JWT access token for user"""

        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        expires_at = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Create JWT payload
        payload = {
            "user_id": user_id,
            "username": user.username,
            "roles": user.roles,
            "exp": expires_at.timestamp(),
            "iat": datetime.now().timestamp()
        }

        # Generate JWT token
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        # Store token
        auth_token = AuthToken(token, user_id, expires_at)
        self.tokens[token] = auth_token

        trace.info(
            f"Token created for user: {user_id}",
            context={
                "user_id": user_id,
                "expires_at": expires_at.isoformat()
            },
            module=__name__,
            function="create_token"
        )

        return token

    @trace_async_calls
    async def verify_token(self, token: str) -> Optional[str]:
        """
        Verify JWT token and return user_id if valid
        """

        try:
            # Decode JWT
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

            user_id = payload.get("user_id")
            exp = payload.get("exp")

            # Check expiration
            if datetime.now().timestamp() > exp:
                trace.warning(
                    "Token expired",
                    context={"user_id": user_id},
                    module=__name__,
                    function="verify_token"
                )
                return None

            # Check if user exists and is active
            user = self.users.get(user_id)
            if not user or not user.is_active:
                trace.warning(
                    "Token verification failed: user not found or inactive",
                    context={"user_id": user_id},
                    module=__name__,
                    function="verify_token"
                )
                return None

            trace.debug(
                "Token verified successfully",
                context={"user_id": user_id},
                module=__name__,
                function="verify_token"
            )

            return user_id

        except jwt.ExpiredSignatureError:
            trace.warning(
                "Token expired (signature)",
                module=__name__,
                function="verify_token"
            )
            return None

        except jwt.InvalidTokenError as e:
            trace.warning(
                "Invalid token",
                module=__name__,
                function="verify_token",
                exception=e
            )
            return None

        except Exception as e:
            trace.error(
                "Error verifying token",
                module=__name__,
                function="verify_token",
                exception=e
            )
            return None

    @trace_async_calls
    async def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return user_id if valid"""

        user_id = self.api_keys.get(api_key)

        if user_id:
            trace.debug(
                "API key verified",
                context={"user_id": user_id},
                module=__name__,
                function="verify_api_key"
            )
        else:
            trace.warning(
                "Invalid API key",
                module=__name__,
                function="verify_api_key"
            )

        return user_id

    @trace_async_calls
    async def revoke_token(self, token: str):
        """Revoke an access token"""

        auth_token = self.tokens.get(token)
        if auth_token:
            auth_token.is_valid = False

            trace.info(
                "Token revoked",
                context={"user_id": auth_token.user_id},
                module=__name__,
                function="revoke_token"
            )

    @trace_async_calls
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission"""

        user = self.users.get(user_id)
        if not user:
            return False

        # Simple role-based permission check
        # In production, implement more granular permissions
        if "admin" in user.roles:
            return True

        permission_mapping = {
            "read_data": ["user", "analyst", "admin"],
            "write_data": ["user", "admin"],
            "manage_users": ["admin"],
            "view_metrics": ["analyst", "admin"]
        }

        allowed_roles = permission_mapping.get(permission, [])
        has_permission = any(role in user.roles for role in allowed_roles)

        trace.debug(
            f"Permission check: {permission} for user {user_id}",
            context={
                "user_id": user_id,
                "permission": permission,
                "result": has_permission
            },
            module=__name__,
            function="check_permission"
        )

        return has_permission

    @trace_async_calls
    async def create_api_key(self, user_id: str) -> str:
        """Create a new API key for user"""

        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        api_key = f"dpoh_{secrets.token_hex(32)}"
        self.api_keys[api_key] = user_id

        trace.info(
            f"API key created for user {user_id}",
            context={"user_id": user_id},
            module=__name__,
            function="create_api_key"
        )

        return api_key

    def get_auth_metrics(self) -> Dict[str, any]:
        """Get authentication service metrics"""
        active_tokens = sum(1 for t in self.tokens.values() if t.is_valid and t.expires_at > datetime.now())

        return {
            "total_users": len(self.users),
            "active_users": sum(1 for u in self.users.values() if u.is_active),
            "total_tokens": len(self.tokens),
            "active_tokens": active_tokens,
            "total_api_keys": len(self.api_keys)
        }
