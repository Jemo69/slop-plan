# Plan: Add Password Authentication to User Model

## Goal
Add bcrypt password hashing to the User model, require passwords for all new registrations, verify passwords on login, and set a password for the existing user `jemolife69@gmail.com`.

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/pyproject.toml` | Edit | Add `passlib[bcrypt]` dependency |
| `backend/models.py` | Edit | Add `password_hash` field to User model |
| `backend/services/__init__.py` | Create | Password hashing utility module |
| `backend/routes/auth.py` | Edit | Update register/login to use password |
| `backend/scripts/set_password.py` | Create | Script to set password for existing user |
| `backend/tests/test_api.py` | Edit | Update tests for password flow |

## Phase 1: Dependencies
- Add `passlib[bcrypt]` to `pyproject.toml` dependencies
- Run `uv sync` to install

## Phase 2: Model Changes
- Add `password_hash = fields.CharField(max_length=255, null=True)` to User model
- `null=True` allows existing users without passwords to still work during transition

## Phase 3: Password Hashing Utility
- Create `backend/services/__init__.py` with:
  - `hash_password(password: str) -> str` using passlib bcrypt
  - `verify_password(password: str, hashed: str) -> bool`

## Phase 4: Auth Route Updates
- `RegisterRequest`: Add `password: str` field (min 6 chars)
- `LoginRequest`: Add `password: str` field
- `register()` endpoint: Hash password, store in `password_hash`
- `login()` endpoint: Verify password against stored hash
- `AuthResponse`: Add `has_password: bool` field for client awareness

## Phase 5: Set Existing User Password
- Create script `backend/scripts/set_password.py`
- Find user by email, hash password `jemolife69.`, update `password_hash`
- Can also be done via a one-time migration in the app

## Phase 6: Test Updates
- Update `test_register_flow` to include password in register/login
- Add test for wrong password login (should fail)
- Add test for missing password (should fail)

## Phase 7: Verification
- Run `pytest` to verify all tests pass
- Run linter/typecheck if available
