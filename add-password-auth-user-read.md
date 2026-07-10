# Add Password Authentication

## What
Add password support to user accounts. Every new user must provide a password when registering. Login now requires both email and password.

## Changes
1. **User model** - New `password_hash` field stores bcrypt-hashed passwords
2. **Register** - Requires `email` + `password` (min 6 chars)
3. **Login** - Requires `email` + `password` (verifies against hash)
4. **Existing user** - `jemolife69@gmail.com` gets password `jemolife69.`

## Files Modified
- `backend/pyproject.toml` - Added passlib dependency
- `backend/models.py` - Added password_hash field
- `backend/services/__init__.py` - New: password hashing functions
- `backend/routes/auth.py` - Updated register/login with password
- `backend/scripts/set_password.py` - New: sets password for existing users
- `backend/tests/test_api.py` - Updated tests

## After
- All new users must set a password
- Login requires password verification
- Existing user can log in with password `jemolife69.`
