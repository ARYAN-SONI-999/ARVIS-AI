import sqlite3
import os
import config

class ArvisMemory:
    def __init__(self, db_path=config.DB_PATH, schema_path=config.SCHEMA_PATH):
        self.db_path = db_path
        self.schema_path = schema_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        # Create database and tables if they don't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Read schema and execute
            with open(self.schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            cursor.executescript(schema_sql)
            conn.commit()
            
            # Migration check: Add embedding column if conversations table exists but misses it
            try:
                cursor.execute("PRAGMA table_info(conversations)")
                columns = [row[1] for row in cursor.fetchall()]
                if columns and "embedding" not in columns:
                    print("Database Migration: Adding 'embedding' column to conversations table...")
                    cursor.execute("ALTER TABLE conversations ADD COLUMN embedding TEXT")
                    conn.commit()
            except Exception as migration_err:
                print(f"Database migration failed: {migration_err}")
                
        except Exception as e:
            print(f"Error initializing SQLite Database: {str(e)}")
        finally:
            conn.close()

    def fetch_embedding(self, text):
        """Fetches 768-dimensional text embedding vector from Gemini Embedding API."""
        api_key = getattr(config, 'GEMINI_API_KEY', '')
        if not api_key or "your_gemini" in api_key.lower():
            return None
            
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
        body = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text}]
            }
        }
        try:
            r = requests.post(url, json=body, timeout=8, verify=False)
            r.raise_for_status()
            res = r.json()
            return res.get("embedding", {}).get("values")
        except Exception as e:
            print(f"⚠️ Failed to fetch embedding: {e}")
            return None

    def cosine_similarity(self, v1, v2):
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_a = sum(a * a for a in v1) ** 0.5
        norm_b = sum(b * b for b in v2) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def save_message(self, session_id, role, content, tokens_used=0):
        try:
            import json
            embedding_val = self.fetch_embedding(content)
            embedding_str = json.dumps(embedding_val) if embedding_val else None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO conversations (session_id, role, content, tokens_used, embedding)
                       VALUES (?, ?, ?, ?, ?)""",
                    (session_id, role, content, tokens_used, embedding_str)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Database error in save_message: {str(e)}")
            return None

    def get_conversation_history(self, session_id, limit=20):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT role, content, timestamp FROM conversations 
                       WHERE session_id = ? 
                       ORDER BY id DESC LIMIT ?""",
                    (session_id, limit)
                )
                rows = cursor.fetchall()
                history = [{"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]} for row in rows]
                history.reverse()
                return history
        except Exception as e:
            print(f"Database error in get_conversation_history: {str(e)}")
            return []

    def log_task(self, action, input_data, output_data, success=True, duration_ms=0, error_msg=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO tasks (action, input_data, output_data, success, duration_ms, error_msg)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (action, input_data, output_data, 1 if success else 0, duration_ms, error_msg)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Database error in log_task: {str(e)}")
            return None

    def get_task_history(self, limit=50):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT id, timestamp, action, input_data, output_data, success, duration_ms, error_msg 
                       FROM tasks ORDER BY id DESC LIMIT ?""",
                    (limit,)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Database error in get_task_history: {str(e)}")
            return []

    def set_preference(self, key, value):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                       VALUES (?, ?, CURRENT_TIMESTAMP)""",
                    (key, str(value))
                )
                conn.commit()
        except Exception as e:
            print(f"Database error in set_preference: {str(e)}")

    def get_preference(self, key, default=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM user_preferences WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                if row:
                    return row["value"]
                return default
        except Exception as e:
            print(f"Database error in get_preference: {str(e)}")
            return default

    def search_past_conversations(self, query, limit=3):
        """Searches past conversations semantically using vector similarity, falling back to keyword search."""
        import json
        
        # Try semantic search
        query_emb = self.fetch_embedding(query)
        if query_emb:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    # Fetch all user messages that have embeddings
                    cursor.execute(
                        """SELECT id, content, timestamp, embedding FROM conversations 
                           WHERE role = 'user' AND embedding IS NOT NULL AND session_id != 'web_session_dummy_temp'"""
                    )
                    rows = cursor.fetchall()
                    
                    matches = []
                    for row in rows:
                        try:
                            emb = json.loads(row["embedding"])
                            if emb:
                                score = self.cosine_similarity(query_emb, emb)
                                matches.append((score, row["id"], row["content"], row["timestamp"]))
                        except Exception:
                            continue
                            
                    # Sort by score descending and take top limits
                    matches.sort(key=lambda x: x[0], reverse=True)
                    top_matches = matches[:limit]
                    
                    results = []
                    for score, user_id, user_content, timestamp in top_matches:
                        # Skip poor matches (similarity threshold)
                        if score < 0.65:
                            continue
                            
                        # Fetch the subsequent assistant response (id = user_id + 1)
                        cursor.execute(
                            "SELECT content FROM conversations WHERE id = ? AND role = 'assistant'",
                            (user_id + 1,)
                        )
                        ass_row = cursor.fetchone()
                        ass_content = ass_row["content"] if ass_row else ""
                        
                        results.append({
                            "user_content": user_content,
                            "assistant_content": ass_content,
                            "timestamp": timestamp
                        })
                    
                    if results:
                        print(f"🧠 [Semantic Memory]: Retrieved {len(results)} relevant past memories.")
                        return results
            except Exception as e:
                print(f"⚠️ Semantic memory search failed: {e}. Falling back to keyword search...")
                
        # Keyword search fallback
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT t1.content AS user_content, t2.content AS assistant_content, t1.timestamp 
                       FROM conversations t1
                       LEFT JOIN conversations t2 ON t2.id = t1.id + 1 AND t2.role = 'assistant'
                       WHERE t1.role = 'user' AND t1.content LIKE ? AND t1.session_id != 'web_session_dummy_temp'
                       ORDER BY t1.id DESC LIMIT ?""",
                    (f"%{query}%", limit)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Database error in search_past_conversations: {str(e)}")
            return []
