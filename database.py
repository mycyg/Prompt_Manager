import sqlite3
import os
import numpy as np
import io

# --- 数据库设置 ---
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'prompts.db')

# 注册numpy array适配器
sqlite3.register_adapter(np.ndarray, lambda arr: sqlite3.Binary(arr.tobytes()))
sqlite3.register_converter("BLOB", lambda b: np.frombuffer(b, dtype=np.float32))

def get_db_connection():
    """创建数据库连接，并启用BLOB转换。"""
    conn = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """使用 schema.sql 文件初始化数据库。"""
    if os.path.exists(DATABASE_PATH):
        # 简单的检查，看embedding列是否存在，不存在则认为需要重建
        conn = get_db_connection()
        try:
            conn.execute("SELECT embedding FROM prompts LIMIT 1")
        except sqlite3.OperationalError:
            conn.close()
            os.remove(DATABASE_PATH) # 删除旧数据库
        else:
            conn.close()
            return

    conn = get_db_connection()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

# --- 提示词 (Prompt) 函数 ---

def add_prompt(title, content, embedding=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO prompts (title, content, embedding) VALUES (?, ?, ?)', 
                   (title, content, embedding))
    prompt_id = cursor.lastrowid
    cursor.execute('INSERT INTO prompt_versions (prompt_id, content) VALUES (?, ?)', (prompt_id, content))
    conn.commit()
    conn.close()
    return prompt_id

def update_prompt(prompt_id, title, content, embedding=None):
    conn = get_db_connection()
    conn.execute('UPDATE prompts SET title = ?, content = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                 (title, content, embedding, prompt_id))
    conn.execute('INSERT INTO prompt_versions (prompt_id, content) VALUES (?, ?)', (prompt_id, content))
    conn.commit()
    conn.close()

def get_all_prompts_with_embeddings():
    """获取所有包含ID和embedding的提示词。"""
    conn = get_db_connection()
    prompts = conn.execute("SELECT id, embedding FROM prompts WHERE embedding IS NOT NULL").fetchall()
    conn.close()
    return prompts

def semantic_search_prompts(query_embedding, limit=10):
    """执行语义搜索并返回排序后的提示词ID列表。"""
    all_prompts = get_all_prompts_with_embeddings()
    if not all_prompts:
        return []

    ids = [p['id'] for p in all_prompts]
    embeddings = np.array([p['embedding'] for p in all_prompts])
    
    # 计算余弦相似度
    query_embedding = query_embedding.reshape(1, -1) # Reshape for broadcasting
    sim = np.dot(embeddings, query_embedding.T) / (np.linalg.norm(embeddings, axis=1, keepdims=True) * np.linalg.norm(query_embedding, keepdims=True))
    sim = sim.flatten()

    # 获取排序后的索引
    sorted_indices = np.argsort(sim)[::-1] # 降序

    # 返回排序后的ID
    sorted_ids = [ids[i] for i in sorted_indices[:limit]]
    return sorted_ids

def get_prompts_by_ids(ids):
    """根据ID列表获取提示词。"""
    if not ids:
        return []
    conn = get_db_connection()
    # 创建占位符字符串
    placeholders = ', '.join('?' * len(ids))
    query = f"SELECT id, title FROM prompts WHERE id IN ({placeholders})"
    # 创建一个字典，用于按输入ID的顺序排序结果
    id_map = {id: i for i, id in enumerate(ids)}
    prompts = conn.execute(query, ids).fetchall()
    conn.close()
    # 按照原始ID列表的顺序排序
    prompts.sort(key=lambda p: id_map[p['id']])
    return prompts

# (Other functions like search_prompts, get_prompt_details, etc. remain)

def search_prompts(query=""):
    conn = get_db_connection()
    if not query:
        prompts = conn.execute('SELECT id, title FROM prompts ORDER BY updated_at DESC').fetchall()
    else:
        search_term = f'%{query}%'
        prompts = conn.execute('''
            SELECT DISTINCT p.id, p.title
            FROM prompts p
            LEFT JOIN prompt_tags pt ON p.id = pt.prompt_id
            LEFT JOIN tags t ON pt.tag_id = t.id
            WHERE p.title LIKE ? OR t.name LIKE ?
            ORDER BY p.updated_at DESC
        ''', (search_term, search_term)).fetchall()
    conn.close()
    return prompts

def get_prompt_details(prompt_id):
    conn = get_db_connection()
    prompt = conn.execute('SELECT * FROM prompts WHERE id = ?', (prompt_id,)).fetchone()
    conn.close()
    return prompt

def delete_prompt(prompt_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM prompts WHERE id = ?', (prompt_id,))
    conn.commit()
    conn.close()

def get_or_create_tag_id(conn, name):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
    tag = cursor.fetchone()
    if tag:
        return tag['id']
    else:
        cursor.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        return cursor.lastrowid

def update_prompt_tags(prompt_id, tags):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM prompt_tags WHERE prompt_id = ?", (prompt_id,))
        for tag_name in tags:
            tag_id = get_or_create_tag_id(conn, tag_name)
            cursor.execute("INSERT INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)", (prompt_id, tag_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"更新标签时出错: {e}")
    finally:
        conn.close()

def get_prompt_tags(prompt_id):
    conn = get_db_connection()
    tags = conn.execute('''
        SELECT t.name FROM tags t
        JOIN prompt_tags pt ON t.id = pt.tag_id
        WHERE pt.prompt_id = ?
    ''', (prompt_id,)).fetchall()
    conn.close()
    return [tag['name'] for tag in tags]

def get_prompt_versions(prompt_id):
    conn = get_db_connection()
    versions = conn.execute('SELECT id, content, saved_at FROM prompt_versions WHERE prompt_id = ? ORDER BY saved_at DESC', (prompt_id,)).fetchall()
    conn.close()
    return versions

def get_version_content(version_id):
    conn = get_db_connection()
    version = conn.execute('SELECT content FROM prompt_versions WHERE id = ?', (version_id,)).fetchone()
    conn.close()
    return version['content'] if version else None
