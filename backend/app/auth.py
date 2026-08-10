"""
JWT Authentication Middleware
Handles JWT token verification for protected routes
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from jwt import decode, InvalidTokenError, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()


class JWTAuthenticator:
    """JWT token authentication and verification"""

    @staticmethod
    def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        Expected format: "Bearer <token>"
        """
        if not authorization:
            return None
        
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                logger.warning(f"Invalid authorization scheme: {scheme}")
                return None
            return token
        except ValueError:
            logger.warning("Invalid Authorization header format")
            return None

    @staticmethod
    def verify_token(token: str) -> dict:
        """
        Verify JWT token signature and expiry.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            # Check token expiry
            exp = payload.get("exp")
            if exp:
                if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                    logger.warning("JWT token has expired")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            
            logger.debug(f"JWT token verified for user: {payload.get('sub')}")
            return payload
            
        except ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Error verifying JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )

    @staticmethod
    def verify_request_token(request: Request) -> dict:
        """
        Extract and verify token from request Authorization header.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is missing or invalid
        """
        authorization = request.headers.get("authorization")
        token = JWTAuthenticator.extract_token_from_header(authorization)
        
        if not token:
            logger.warning("Missing or invalid Authorization header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return JWTAuthenticator.verify_token(token)


async def jwt_verification_middleware(request: Request, call_next):
    """
    Middleware for JWT verification on protected routes.
    
    Protected routes patterns:
    - /admin/*
    - /api/admin/*
    - /backtest/run
    - /api/backtesting/run
    
    Public routes (excluded):
    - /api/signals
    - /api/news
    - /api/health
    - /health
    - /ws/*
    - /api/ws/*
    """
    
    # Define public routes that don't require authentication
    public_paths = [
        "/",
        "/api/health",
        "/health",
        "/api/signals",
        "/api/news",
    ]
    
    # Define protected route patterns
    protected_patterns = [
        "/admin/",
        "/api/admin/",
        "/backtest/run",
        "/api/backtesting/run",
    ]
    
    # Check if path is public
    path = request.url.path
    is_public = path in public_paths or path.startswith(("/ws/", "/api/ws/"))
    
    # Check if path matches protected patterns
    is_protected = any(path.startswith(pattern) for pattern in protected_patterns)
    
    if is_protected and not is_public:
        try:
            # Extract and verify JWT token
            payload = JWTAuthenticator.verify_request_token(request)
            # Store token payload in request state for later use
            request.state.user = payload
            logger.debug(f"Successfully authenticated request to {path}")
        except HTTPException:
            raise
    
    response = await call_next(request)
    return response
