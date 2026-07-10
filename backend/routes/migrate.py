from fastapi import APIRouter, HTTPException, Depends
from routes.auth import get_current_user
from models import User

router = APIRouter()


@router.post("/migrate-approval")
async def migrate_approval(user: User = Depends(get_current_user)):
    """Add approval columns to plans table."""
    from tortoise.connection import connections
    conn = connections.get("default")
    
    statements = [
        "ALTER TABLE plans ADD COLUMN is_approved BOOLEAN DEFAULT FALSE",
        "ALTER TABLE plans ADD COLUMN approved_at TIMESTAMP NULL",
        "ALTER TABLE plans ADD COLUMN approved_by TEXT NULL",
    ]
    
    results = []
    for stmt in statements:
        try:
            await conn.execute_query(stmt)
            results.append(f"OK: {stmt}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                results.append(f"SKIP (already exists): {stmt}")
            else:
                results.append(f"ERROR: {stmt} -> {e}")
    
    return {"results": results}
