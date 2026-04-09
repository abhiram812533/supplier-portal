from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supplier_secret"

# ---------- DB CONNECTION ----------
def get_db():
    return sqlite3.connect("database.db")

# ---------- INIT DB ----------
def init_db():
    db = get_db()
    c = db.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        cost_price INTEGER,
        sell_price INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product TEXT,
        quantity INTEGER,
        total INTEGER,
        payment TEXT,
        date TEXT
    )
    """)

    # Default admin
    c.execute("SELECT * FROM users WHERE role='admin'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO users (name, username, password, role)
            VALUES (?, ?, ?, ?)
        """, ("Admin", "admin", "admin", "admin"))

    db.commit()
    db.close()

init_db()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        user = c.fetchone()
        db.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[4]

            if user[4] == "admin":
                return redirect("/admin")
            else:
                return redirect("/customer")

    return render_template("login.html")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- ADMIN DASHBOARD ----------
@app.route("/admin")
def admin():
    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    db = get_db()
    c = db.cursor()

    # Orders table with customer name
    c.execute("""
        SELECT u.name, o.product, o.quantity, o.total, o.payment
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.id DESC
    """)
    orders = c.fetchall()

    # Product-wise stats
    c.execute("""
        SELECT product,
               SUM(quantity) AS total_qty,
               SUM(total) AS revenue
        FROM orders
        GROUP BY product
    """)
    stats = c.fetchall()

    db.close()
    return render_template(
        "admin_dashboard.html",
        orders=orders,
        stats=stats
    )

# ---------- ADD PRODUCT ----------
@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    if request.method == "POST":
        name = request.form["name"]
        cp = int(request.form["cp"])
        sp = int(request.form["sp"])

        db = get_db()
        db.execute(
            "INSERT INTO products (name, cost_price, sell_price) VALUES (?, ?, ?)",
            (name, cp, sp)
        )
        db.commit()
        db.close()

        return redirect("/admin")

    return render_template("add_product.html")

# ---------- ADD CUSTOMER ----------
@app.route("/add-customer", methods=["GET", "POST"])
def add_customer():
    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        db.execute(
            "INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
            (name, username, password, "customer")
        )
        db.commit()
        db.close()

        return redirect("/admin")

    return render_template("add_customer.html")

# ---------- CHANGE PASSWORD ----------
@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        new = request.form["new"]

        db = get_db()
        db.execute(
            "UPDATE users SET password=? WHERE id=?",
            (new, session["user_id"])
        )
        db.commit()
        db.close()

        return redirect("/admin")

    return render_template("change_password.html")

# ---------- CUSTOMER DASHBOARD ----------
@app.route("/customer", methods=["GET", "POST"])
def customer():
    if "role" not in session or session["role"] != "customer":
        return redirect("/")

    db = get_db()
    c = db.cursor()

    c.execute("SELECT id, name, sell_price FROM products")
    products = c.fetchall()

    if request.method == "POST":
        payment = request.form["payment"]

        for p in products:
            pid = p[0]
            pname = p[1]
            price = p[2]

            qty = request.form.get(f"qty_{pid}")

            if qty and qty.isdigit() and int(qty) > 0:
                qty = int(qty)
                total = qty * price

                c.execute("""
                    INSERT INTO orders
                    (user_id, product, quantity, total, payment, date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session["user_id"],
                    pname,
                    qty,
                    total,
                    payment,
                    datetime.now()
                ))

        db.commit()

    db.close()
    return render_template("customer_dashboard.html", products=products)

# ---------- CUSTOMER HISTORY ----------
@app.route("/customer-history")
def customer_history():
    if "role" not in session or session["role"] != "customer":
        return redirect("/")

    db = get_db()
    c = db.cursor()

    c.execute("""
        SELECT product, quantity, total, payment, date
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
    """, (session["user_id"],))

    history = c.fetchall()
    db.close()

    return render_template("customer_history.html", history=history)

# ---------- RUN ----------
app.run(debug=True)
