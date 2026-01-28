"""
Configuration validation for ProfileGPT.

Ensures secure configuration in production environments while allowing
flexible development workflows.
"""

import secrets
import sys

# Known weak secrets that should never be used
WEAK_SECRETS = {
    'dev-secret-key-change-in-production',
    '4737d354',
    '123450',
    'dev',
    'test',
    'secret',
    'changeme',
    'insecure',
}

def generate_development_secret():
    """Generate a secure random secret key for development use."""
    return secrets.token_hex(32)

def validate_flask_secret_key(secret_key, is_local_mode):
    """
    Validate Flask secret key strength.

    Args:
        secret_key: The secret key to validate (or None if not set)
        is_local_mode: Whether running in local development mode

    Returns:
        tuple: (validated_key, warning_message or None)

    Raises:
        ValueError: If validation fails in production mode
    """
    # Handle missing secret key
    if not secret_key:
        if is_local_mode:
            generated = generate_development_secret()
            warning = (
                "WARNING: FLASK_SECRET_KEY not set. Auto-generated a secure key for this session.\n"
                "For production, generate a persistent key with:\n"
                "  python -c \"import secrets; print(secrets.token_hex(32))\""
            )
            return generated, warning
        else:
            raise ValueError(
                "FLASK_SECRET_KEY environment variable is required.\n"
                "Generate a secure key with:\n"
                "  python -c \"import secrets; print(secrets.token_hex(32))\"\n"
                "Then set it in your environment or .env file."
            )

    # Check minimum length
    if len(secret_key) < 32:
        if is_local_mode:
            warning = (
                f"WARNING: FLASK_SECRET_KEY is only {len(secret_key)} characters (minimum 32 recommended).\n"
                "Generate a secure key with:\n"
                "  python -c \"import secrets; print(secrets.token_hex(32))\""
            )
            return secret_key, warning
        else:
            raise ValueError(
                f"FLASK_SECRET_KEY must be at least 32 characters (got {len(secret_key)}).\n"
                "Generate a secure key with:\n"
                "  python -c \"import secrets; print(secrets.token_hex(32))\""
            )

    # Check against known weak secrets
    if secret_key in WEAK_SECRETS:
        if is_local_mode:
            warning = (
                f"WARNING: FLASK_SECRET_KEY is a known weak value.\n"
                "Generate a secure key with:\n"
                "  python -c \"import secrets; print(secrets.token_hex(32))\""
            )
            return secret_key, warning
        else:
            raise ValueError(
                "FLASK_SECRET_KEY is a known weak value and cannot be used in production.\n"
                "Generate a secure key with:\n"
                "  python -c \"import secrets; print(secrets.token_hex(32))\""
            )

    # Valid secret key
    return secret_key, None

def validate_admin_reset_key(reset_key, is_local_mode):
    """
    Validate admin reset key if provided.

    Args:
        reset_key: The admin reset key to validate (or None if not set)
        is_local_mode: Whether running in local development mode

    Returns:
        tuple: (validated_key or None, warning_message or None)
    """
    # Admin reset key is optional
    if not reset_key:
        return None, None

    # If set, should be strong
    if len(reset_key) < 16:
        warning = (
            f"WARNING: ADMIN_RESET_KEY is only {len(reset_key)} characters (minimum 16 recommended).\n"
            "Generate a secure key with:\n"
            "  python -c \"import secrets; print(secrets.token_hex(16))\""
        )
        if is_local_mode:
            return reset_key, warning
        else:
            # In production, warn but don't fail (it's optional)
            print(warning, file=sys.stderr)
            return reset_key, None

    # Check against known weak values
    if reset_key in WEAK_SECRETS:
        warning = (
            "WARNING: ADMIN_RESET_KEY is a known weak value.\n"
            "Generate a secure key with:\n"
            "  python -c \"import secrets; print(secrets.token_hex(16))\""
        )
        if is_local_mode:
            return reset_key, warning
        else:
            # In production, warn but don't fail (it's optional)
            print(warning, file=sys.stderr)
            return reset_key, None

    return reset_key, None
