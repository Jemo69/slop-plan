import os
from dotenv import load_dotenv
import libsql_experimental as libsql

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "local.db")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", None)


def get_connection():
    if TURSO_AUTH_TOKEN:
        return libsql.connect(
            database=f"libsql://{DATABASE_URL}",
            auth_token=TURSO_AUTH_TOKEN,
        )
    else:
        return libsql.connect(database=DATABASE_URL)


async def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            html_content TEXT NOT NULL,
            frontmatter TEXT,
            is_public INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    conn.commit()
    conn.close()
