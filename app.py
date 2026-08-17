import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)  # ከFrontend የሚመጡ ጥሪዎችን ለመቀበል (Cross-Origin)

# የPostgreSQL ዳታቤዝ ማገናኛ (Vercel Postgres/Neon/Supabase URL)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/micro_store")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# የዳታቤዝ ቴብሎችን የመፍጠሪያ ተግባር
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            phone VARCHAR(20) PRIMARY KEY,
            store_name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            seller_phone VARCHAR(20) REFERENCES stores(phone),
            name VARCHAR(100) NOT NULL,
            price NUMERIC(10, 2) NOT NULL,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# ኤፒአይ ለሱቅ ምዝገባ ወይም መግቢያ
@app.route('/api/register-store', methods=['POST'])
def register_store():
    data = request.json
    phone = data.get('phone')
    store_name = data.get('store_name', 'የእኔ ሱቅ')

    if not phone:
        return jsonify({'error': 'የስልክ ቁጥር ያስፈልጋል'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO stores (phone, store_name)
        VALUES (%s, %s)
        ON CONFLICT (phone) DO UPDATE SET store_name = EXCLUDED.store_name;
    """, (phone, store_name))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'message': 'ሱቅ በተሳካ ሁኔታ ተመዝግቧል/ገብቷል'}), 200

# ኤፒአይ አዲስ ምርት ለመጨመር
@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    seller_phone = data.get('seller_phone')
    name = data.get('name')
    price = data.get('price')
    image_url = data.get('image_url', 'https://via.placeholder.com/150')

    if not seller_phone or not name or not price:
        return jsonify({'error': 'ሁሉንም አስፈላጊ መረጃዎች ያስገቡ'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO products (seller_phone, name, price, image_url)
        VALUES (%s, %s, %s, %s) RETURNING id;
    """, (seller_phone, name, price, image_url))
    new_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'message': 'ምርቱ ተመዝግቧል', 'product_id': new_id}), 201

# ኤፒአይ የነጋዴውን ምርቶች ዝርዝር ለማውጣት
@app.route('/api/products/<phone>', methods=['GET'])
def get_products(phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, price, image_url, created_at
        FROM products WHERE seller_phone = %s
        ORDER BY created_at DESC;
    """, (phone,))
    products = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(products), 200

if __name__ == '__main__':
    # በመጀመሪያ ጊዜ ሲበራ ቴብሎችን መፍጠር
    try:
        init_db()
    except Exception as e:
        print("DB init error:", e)
    app.run(debug=True, port=5000)
