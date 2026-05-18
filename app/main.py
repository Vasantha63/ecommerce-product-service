from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import PlainTextResponse
import sqlite3
import uvicorn

app = FastAPI(title="E-Commerce Product Service")

# Prometheus metrics
request_counter = Counter("product_requests_total", "Total requests", ["method", "endpoint"])
request_latency = Histogram("product_request_latency_seconds", "Request latency")

# Database setup
def get_db():
    conn = sqlite3.connect("products.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            category TEXT
        )
    """)
    conn.execute("INSERT OR IGNORE INTO products (id, name, price, stock, category) VALUES (1, 'Laptop', 50000, 10, 'Electronics')")
    conn.execute("INSERT OR IGNORE INTO products (id, name, price, stock, category) VALUES (2, 'Phone', 20000, 25, 'Electronics')")
    conn.execute("INSERT OR IGNORE INTO products (id, name, price, stock, category) VALUES (3, 'Shirt', 500, 100, 'Clothing')")
    conn.commit()
    conn.close()

init_db()

# Models
class Product(BaseModel):
    name: str
    price: float
    stock: int
    category: Optional[str] = None

# Routes
@app.get("/products")
def get_products():
    request_counter.labels(method="GET", endpoint="/products").inc()
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return [dict(p) for p in products]

@app.get("/products/{product_id}")
def get_product(product_id: int):
    request_counter.labels(method="GET", endpoint="/products/id").inc()
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return dict(product)

@app.post("/products")
def create_product(product: Product):
    request_counter.labels(method="POST", endpoint="/products").inc()
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO products (name, price, stock, category) VALUES (?, ?, ?, ?)",
        (product.name, product.price, product.stock, product.category)
    )
    conn.commit()
    conn.close()
    return {"id": cursor.lastrowid, "message": "Product created!"}

@app.put("/products/{product_id}")
def update_product(product_id: int, product: Product):
    request_counter.labels(method="PUT", endpoint="/products/id").inc()
    conn = get_db()
    conn.execute(
        "UPDATE products SET name=?, price=?, stock=?, category=? WHERE id=?",
        (product.name, product.price, product.stock, product.category, product_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Product updated!"}

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    request_counter.labels(method="DELETE", endpoint="/products/id").inc()
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    return {"message": "Product deleted!"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "product-service"}

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return generate_latest()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)