"""Authentication & authorization security primitives.

password.py: bcrypt hashing/verification.
jwt.py: access/refresh token creation and verification.
dependencies.py: FastAPI OAuth2/JWT-bearer dependencies (get_current_user,
require_role, etc.) used to protect routes.

Kept separate from app/core/ (generic app plumbing) since this is a
distinct, security-sensitive concern with its own file grouping, per
the architecture the sprint asked for (Models / Schemas / Repositories
/ Services / Security / Dependencies / Routes).
"""
