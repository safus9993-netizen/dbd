import streamlit as st
import pandas as pd
from sqlalchemy import text

def get_connection():
    # Streamlit automatically finds [connections.supabase] in .streamlit/secrets.toml
    return st.connection("supabase", type="sql", autocommit=True)

def init_db():
    conn = get_connection()
    with conn.session as s:
        # PostgreSQL uses SERIAL for auto-incrementing ID
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS restaurants (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS menu_items (
                id SERIAL PRIMARY KEY,
                restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                price INTEGER NOT NULL
            )
        '''))
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
                deadline TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                user_name TEXT NOT NULL,
                item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
                quantity INTEGER DEFAULT 1,
                note TEXT,
                has_paid INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        '''))
        
        # Initialize default admin
        count = s.execute(text('SELECT COUNT(*) FROM admins')).scalar()
        if count == 0:
            s.execute(text("INSERT INTO admins (username, password) VALUES ('admin', 'admin')"))
        
        s.commit()

# --- Admins ---
def add_admin(username, password):
    conn = get_connection()
    with conn.session as s:
        try:
            s.execute(text('INSERT INTO admins (username, password) VALUES (:u, :p)'), {"u": str(username), "p": str(password)})
            s.commit()
            return True
        except Exception:
            s.rollback()
            return False

def get_admins():
    return get_connection().query('SELECT id, username FROM admins', ttl=0)

def delete_admin(admin_id):
    conn = get_connection()
    with conn.session as s:
        count = s.execute(text('SELECT COUNT(*) FROM admins')).scalar()
        if count > 1:
            s.execute(text('DELETE FROM admins WHERE id = :id'), {"id": int(admin_id)})
            s.commit()
            return True
        return False

def verify_admin(username, password):
    if not username or not password:
        return False
    conn = get_connection()
    with conn.session as s:
        result = s.execute(text('SELECT id FROM admins WHERE username = :u AND password = :p'), {"u": str(username), "p": str(password)}).fetchone()
        return result is not None

# --- Restaurants ---
def add_restaurant(name, phone):
    conn = get_connection()
    with conn.session as s:
        s.execute(text('INSERT INTO restaurants (name, phone) VALUES (:n, :p)'), {"n": str(name), "p": str(phone)})
        s.commit()

def get_restaurants():
    return get_connection().query('SELECT * FROM restaurants', ttl=0)

def delete_restaurant(rest_id):
    conn = get_connection()
    with conn.session as s:
        s.execute(text('DELETE FROM menu_items WHERE restaurant_id = :id'), {"id": int(rest_id)})
        s.execute(text('DELETE FROM restaurants WHERE id = :id'), {"id": int(rest_id)})
        s.commit()

# --- Menus ---
def add_menu_item(restaurant_id, name, price):
    conn = get_connection()
    with conn.session as s:
        s.execute(text('INSERT INTO menu_items (restaurant_id, name, price) VALUES (:rid, :n, :p)'), 
                  {"rid": int(restaurant_id), "n": str(name), "p": int(price)})
        s.commit()

def get_menu(restaurant_id):
    return get_connection().query('SELECT * FROM menu_items WHERE restaurant_id = :id', params={"id": int(restaurant_id)}, ttl=0)

def delete_menu_item(item_id):
    conn = get_connection()
    with conn.session as s:
        s.execute(text('DELETE FROM menu_items WHERE id = :id'), {"id": int(item_id)})
        s.commit()

# --- Sessions ---
def create_session(date, restaurant_id, deadline):
    conn = get_connection()
    with conn.session as s:
        s.execute(text('INSERT INTO sessions (date, restaurant_id, deadline) VALUES (:d, :rid, :dl)'),
                  {"d": str(date), "rid": int(restaurant_id), "dl": str(deadline)})
        s.commit()

def get_active_sessions():
    query = '''
        SELECT s.id, s.date, s.deadline, s.is_active, s.restaurant_id, r.name as restaurant_name, r.phone
        FROM sessions s
        JOIN restaurants r ON s.restaurant_id = r.id
        WHERE s.is_active = 1
        ORDER BY s.id DESC
    '''
    return get_connection().query(query, ttl=0)

def close_session(session_id):
    conn = get_connection()
    with conn.session as s:
        s.execute(text('UPDATE sessions SET is_active = 0 WHERE id = :id'), {"id": int(session_id)})
        s.commit()

def delete_session(session_id):
    conn = get_connection()
    with conn.session as s:
        s.execute(text('DELETE FROM orders WHERE session_id = :id'), {"id": int(session_id)})
        s.execute(text('DELETE FROM sessions WHERE id = :id'), {"id": int(session_id)})
        s.commit()

# --- Orders ---
def place_order(session_id, user_name, item_id, quantity, note):
    conn = get_connection()
    with conn.session as s:
        s.execute(text('''
            INSERT INTO orders (session_id, user_name, item_id, quantity, note)
            VALUES (:sid, :un, :iid, :q, :note)
        '''), {"sid": int(session_id), "un": str(user_name), "iid": int(item_id), "q": int(quantity), "note": str(note)})
        s.commit()

def get_orders_for_session(session_id):
    query = '''
        SELECT o.id, o.user_name, m.name as item_name, m.price, o.quantity, 
               (m.price * o.quantity) as total_price, o.note, o.has_paid, o.created_at
        FROM orders o
        JOIN menu_items m ON o.item_id = m.id
        WHERE o.session_id = :sid
        ORDER BY o.created_at DESC
    '''
    return get_connection().query(query, params={"sid": int(session_id)}, ttl=0)

def toggle_payment_status(order_id, current_status):
    conn = get_connection()
    with conn.session as s:
        new_status = 0 if current_status == 1 else 1
        s.execute(text('UPDATE orders SET has_paid = :ns WHERE id = :id'), {"ns": new_status, "id": int(order_id)})
        s.commit()

try:
    init_db()
except Exception:
    pass
