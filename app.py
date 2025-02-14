# region Setup and Configuration
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User  # Adjust the import path based on your project structure
import sqlite3
from sqlite3 import IntegrityError
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import os
app = Flask(__name__)



# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Replace with your actual DB URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Optional: disable modification tracking

# Initialize SQLAlchemy and Migrate instances
db = SQLAlchemy(app)
migrate = Migrate(app, db)
app.permanent_session_lifetime = timedelta(minutes=60)
app.secret_key = "your_secret_key"  # Needed for session management


ALLOWED_IPS = ['192.168.0.18', '192.168.0.129', '192.168.0.55', '192.168.0.79'
               , '192.168.0.131', '192.168.0.238']  # Add your phone's IP

@app.before_request
def restrict_access():
    if request.remote_addr not in ALLOWED_IPS:
        abort(403)  # Forbidden

# endregion

# region Database Utilities
def get_db_connection():
    conn = sqlite3.connect('database.db', timeout=30)  # Add a timeout of 10 seconds
    conn.row_factory = sqlite3.Row
    return conn

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Helper function to query the database
def query_db(query, args=(), one=False):
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
    return (rv[0] if rv else None) if one else rv
#endregion

#region Init_DB

@app.route('/init_db')
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if 'full_name' column already exists
    cursor.execute("PRAGMA table_info(users);")
    columns = [column[1] for column in cursor.fetchall()]



    conn.close()

    print("Database initialized.")

#endregion

# region User Authentication and Session Management
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_role"] = user["role"]  # Store the user's role in the session
            flash(f"Welcome, {username}!", "success")

            # Redirect based on user role
            if user["role"] == "Admin":
                return redirect(url_for("dashboard"))  # Example route for Admin
            elif user["role"] == "Storeworker":
                return redirect(url_for("dashboard"))
            else:
                return redirect(url_for("dashboard"))  # Default fallback
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

class User(db.Model):
    __tablename__ = 'users'  # Explicitly set the table name

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)


@app.route("/customer_login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        clinic_username = request.form["clinic_username"]
        clinic_password = request.form["clinic_password"]

        conn = get_db_connection()
        customer = conn.execute(
            "SELECT * FROM customer_account WHERE clinic_username = ?", (clinic_username,)
        ).fetchone()
        conn.close()

        if customer and check_password_hash(customer["clinic_password"], clinic_password):
            session["customer_id"] = customer["id"]
            session["user_role"] = "customer"
            flash(f"Welcome, {customer['clinic_name']}!", "success")
            return redirect(url_for("customer_menu"))
        else:
            flash("Invalid clinic username or password.", "danger")

    return render_template("login.html")

@app.context_processor
def inject_user_details():
    user_role = None
    priority_customer = False

    # For customers
    if "customer_id" in session:
        conn = get_db_connection()
        customer = conn.execute(
            "SELECT clinic_username, priority_customer FROM customer_account WHERE id = ?",
            (session["customer_id"],)
        ).fetchone()
        conn.close()
        if customer:
            user_role = "Customer"
            priority_customer = bool(customer["priority_customer"])

    # For other user types
    elif "user_id" in session:
        conn = get_db_connection()
        user = conn.execute("SELECT role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()
        if user:
            user_role = user["role"]

    return {"user_role": user_role, "priority_customer": priority_customer}


@app.context_processor
def inject_logged_in_user():
    user_name = None
    if "user_id" in session:
        conn = get_db_connection()
        user = conn.execute("SELECT full_name FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()
        if user:
            user_name = user["full_name"]
    elif "customer_id" in session:
        conn = get_db_connection()
        customer = conn.execute("SELECT clinic_name FROM customer_account WHERE id = ?", (session["customer_id"],)).fetchone()
        conn.close()
        if customer:
            user_name = customer["clinic_name"]
    return {"logged_in_user": user_name}





# Route: Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

#endregion

# region Dashboard
@app.route("/dashboard")
def dashboard():
    # Ensure the user is logged in
    if "user_id" not in session:
        flash("You need to log in to access the dashboard.", "warning")
        return redirect(url_for("login"))

    # Check user role
    conn = get_db_connection()
    user = conn.execute("SELECT role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()

    # Allow access only for storeworkers, supervisors, and admins
    allowed_roles = ["Storeworker", "Supervisor", "Admin"]
    if user and user["role"] not in allowed_roles:
        flash("Access restricted. You do not have permission to view this page.", "danger")
        return redirect(url_for("main_menu"))  # Redirect to the main menu or login page

    # Fetch dashboard data
    conn = get_db_connection()
    orders = conn.execute("""
        SELECT 
            o.*,
            ca.priority_customer,
            DATETIME(o.finalized_time, '+3 hours') > DATETIME('now') AS is_new,
            o.finalized_by,
            COALESCE(ca.preferred_carrier, o.carrier) AS carrier
        FROM orders o
        LEFT JOIN customer_account ca 
        ON o.clinic_name = ca.clinic_name
        WHERE o.order_confirmed = 'Confirmed'
        ORDER BY o.finalized_time DESC
    """).fetchall()
    conn.close()

    return render_template("dashboard.html", orders=[dict(order) for order in orders])



#endregion

#region Admin

def check_admin():
    user_id = session.get("user_id")
    if not user_id:
        flash("You need to log in.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    user = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if user["role"] != "Admin":
        flash("Access restricted to Admins only.", "danger")
        return redirect(url_for("dashboard"))


#endregion

# region Menu

#endregion

#region Main Menu

@app.route("/main_menu")
def main_menu():
    if "user_id" not in session:
        flash("You need to log in.", "warning")
        return redirect(url_for("login"))

    user_role = session.get("user_role")
    return render_template("main_menu.html", user_role=user_role)


#endregion

# region User Management

@app.route("/update_user_role", methods=["POST"])
def update_user_role():
    # Ensure the user is an Admin
    if not session.get("user_id"):
        flash("You need to log in.", "warning")
        return redirect(url_for("login"))

    # Get the user's role from the database
    conn = get_db_connection()
    user = conn.execute("SELECT role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()

    if user["role"] != "Admin":
        flash("Access restricted to Admins only.", "danger")
        return redirect(url_for("dashboard"))

    # Get the user ID and new role from the form
    user_id = request.form.get("user_id")
    new_role = request.form.get("role")

    # Update the user's role
    conn = get_db_connection()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()

    flash("User role updated successfully!", "success")
    return redirect(url_for("manage_users"))

# Route: Render Create Account Page
@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        try:
            # Check if username already exists
            query_db("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, hashed_password, 'storeworker'))
            flash("Account successfully created!", "success")
            return redirect(url_for("login"))  # Redirect to login page after successful creation
        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose a different one.", "danger")
            return render_template("create_account.html")  # Return to the account creation page if username exists

    return render_template("create_account.html")  # Render the form on GET request


@app.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        new_role = request.form.get("role")

        conn = get_db_connection()
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        conn.close()

        flash("User role updated successfully!", "success")
        return redirect(url_for("users"))

    conn = get_db_connection()
    users = conn.execute("SELECT id, full_name, username, role FROM users").fetchall()
    conn.close()

    return render_template("users.html", users=users)

@app.route("/add_user", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        full_name = request.form["full_name"]
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]  # Get the selected role from the form
        hashed_password = generate_password_hash(password)

        try:
            # Insert the user into the database with full name, username, password hash, and selected role
            query_db("INSERT INTO users (full_name, username, password_hash, role) VALUES (?, ?, ?, ?)",
                     (full_name, username, hashed_password, role))
            flash("User created successfully!", "success")
            return redirect(url_for("users"))  # Redirect to users page after creation
        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose a different one.", "danger")
            return render_template("add_user.html")  # Return to the form if username already exists

    return render_template("add_user.html")  # Render the user creation form when the route is accessed via GET


@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    # Ensure the user is logged in and is an Admin
    if not session.get("user_id"):
        flash("You need to log in.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    # Fetch the user's current details
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("users"))

    # Handle the form submission for updating user details
    if request.method == "POST":
        full_name = request.form["full_name"]
        username = request.form["username"]
        password = request.form["password"]

        # If the password is not empty, hash it and update it, otherwise preserve the old password
        if password:
            hashed_password = generate_password_hash(password)
        else:
            hashed_password = user["password_hash"]  # Keep the existing password hash if not updating

        role = request.form["role"]  # Get the new role from the form

        # Update the user's information
        conn = get_db_connection()
        conn.execute("""
            UPDATE users 
            SET full_name = ?, username = ?, password_hash = ?, role = ?
            WHERE id = ?
        """, (full_name, username, hashed_password, role, user_id))
        conn.commit()
        conn.close()

        flash("User updated successfully!", "success")
        return redirect(url_for("users"))

    return render_template("edit_user.html", user=user)


# Route: Delete User
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    # Ensure the user is logged in and is an Admin
    if not session.get("user_id"):
        flash("You need to log in.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("manage_users"))

    # Delete user from the database
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("User deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting user: {str(e)}", "danger")

    return redirect(url_for("users"))


@app.route('/manage_users')
def manage_users():
    users = User.query.all()  # Adjust based on your database model
    return render_template('users.html', users=users)


#endregion

#region Database (Old Order Screen)

# Route: Database Entries Page
@app.route('/database', methods=['GET'])
def database_entries():
    conn = get_db_connection()

    # Retrieve search and sort parameters
    search_query = request.args.get('search', '')
    sort_column = request.args.get('sort_column', 'order_id')
    sort_order = request.args.get('sort_order', 'asc')  # Default to ascending

    # Build the base query
    query = 'SELECT * FROM orders WHERE 1=1'
    params = []

    # Apply search filter if provided (exclude finalized_time)
    if search_query:
        query += """
        AND (
            order_id LIKE ? OR
            description LIKE ? OR
            lines LIKE ? OR
            quantity LIKE ? OR
            clinic_name LIKE ? OR
            clinic_address LIKE ? OR
            finalized_by LIKE ? OR
            carrier LIKE ? OR
            category LIKE ? OR
            status LIKE ?
        )
        """
        search_pattern = f"%{search_query}%"
        params.extend([search_pattern] * 10)  # Exclude finalized_time

    # Get the total record count before sorting and filtering
    total_records_query = 'SELECT COUNT(*) FROM orders'
    total_records = conn.execute(total_records_query).fetchone()[0]

    # Apply sorting
    query += f' ORDER BY {sort_column} {sort_order.upper()}'

    # Execute the query
    filtered_orders = conn.execute(query, params).fetchall()
    filtered_count = len(filtered_orders)  # Count of filtered records

    # Fetch carriers for the dropdown
    carriers = conn.execute('SELECT name FROM carriers').fetchall()

    conn.close()

    return render_template(
        'database_entries.html',
        orders=filtered_orders,
        search_query=search_query,
        sort_column=sort_column,
        sort_order=sort_order,
        total_records=total_records,
        filtered_count=filtered_count,
        carriers=carriers  # Pass carriers to the template
    )

# Route: Add New Entry



# Route: Fetch Order Details for Modal
@app.route('/get_order_items/<int:order_id>', methods=['GET'])
def get_order_items(order_id):
    conn = get_db_connection()

    # Fetch order details
    order = conn.execute("""
        SELECT o.*, 
               c.priority_customer 
        FROM orders o
        LEFT JOIN customer_account c 
        ON o.clinic_name = c.clinic_name
        WHERE o.order_id = ?
    """, (order_id,)).fetchone()

    # Fetch items in the order
    items = conn.execute("""
        SELECT oi.item_name AS name, 
               oi.quantity, 
               p.price 
        FROM order_items oi
        LEFT JOIN products p 
        ON oi.item_name = p.product_name
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()

    conn.close()

    if not order:
        return jsonify({"error": "Order not found"}), 404

    return jsonify({
        "order_id": order["order_id"],
        "clinic_name": order["clinic_name"],
        "clinic_address": order["clinic_address"],
        "finalized_time": order["finalized_time"],
        "finalized_by": order["finalized_by"],
        "carrier": order["carrier"],
        "category": order["category"],
        "status": order["status"],
        "priority_customer": bool(order["priority_customer"]),
        "description": order["description"],
        "items": [dict(item) for item in items]
    })


# Route: Update Order Status




#endregion

#region Order Records

# ***** ORDER RECORDS VIEW (Admin only) *****
@app.route("/order_records", methods=["GET"])
def order_records():
    # Ensure only admin users access this page.
    if "user_id" not in session or session.get("user_role") != "Admin":
        flash("Access restricted to admins only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    # Get search parameters: search_field and search_value from query string.
    search_field = request.args.get("search_field", "")
    search_value = request.args.get("search_value", "")
    base_query = "SELECT * FROM orders"
    params = []
    if search_field and search_value:
        # Allowed search fields (columns) – adjust as needed.
        allowed_fields = ["description", "lines", "quantity", "clinic_name", "clinic_address",
                          "finalized_time", "finalized_by", "carrier", "category", "status",
                          "allocated_to", "order_confirmed"]
        if search_field not in allowed_fields:
            flash("Invalid search field.", "danger")
            return redirect(url_for("order_records"))
        base_query += " WHERE {} LIKE ?".format(search_field)
        params.append(f"%{search_value}%")

    orders = conn.execute(base_query, params).fetchall()
    total_records = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    filtered_count = len(orders)
    conn.close()

    return render_template("order_records.html",
                           orders=[dict(o) for o in orders],
                           search_field=search_field,
                           search_value=search_value,
                           total_records=total_records,
                           filtered_count=filtered_count)


# ***** EDIT ORDER (AJAX endpoint) *****
@app.route("/edit_order", methods=["POST"])
def edit_order():
    if "user_id" not in session or session.get("user_role") != "Admin":
        return jsonify({"error": "Access restricted to admins."}), 403

    data = request.get_json()
    order_id = data.get("order_id")
    # Get all editable fields (all except order_id)
    description = data.get("description")
    lines = data.get("lines")
    quantity = data.get("quantity")
    clinic_name = data.get("clinic_name")
    clinic_address = data.get("clinic_address")
    finalized_time = data.get("finalized_time")
    finalized_by = data.get("finalized_by")
    carrier = data.get("carrier")
    category = data.get("category")
    status = data.get("status")
    allocated_to = data.get("allocated_to")
    order_confirmed = data.get("order_confirmed")

    conn = get_db_connection()
    conn.execute("""
        UPDATE orders SET
            description = ?,
            lines = ?,
            quantity = ?,
            clinic_name = ?,
            clinic_address = ?,
            finalized_time = ?,
            finalized_by = ?,
            carrier = ?,
            category = ?,
            status = ?,
            allocated_to = ?,
            order_confirmed = ?
        WHERE order_id = ?
    """, (description, lines, quantity, clinic_name, clinic_address, finalized_time,
          finalized_by, carrier, category, status, allocated_to, order_confirmed, order_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Order updated successfully!"})


# ***** DELETE ORDER (AJAX endpoint) *****
@app.route("/delete_order/<int:order_id>", methods=["POST"])
def delete_order(order_id):
    if "user_id" not in session or session.get("user_role") != "Admin":
        return jsonify({"error": "Access restricted to admins."}), 403

    conn = get_db_connection()
    conn.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


#endregion

#region Re-Directs

# Redirect `/product_database` to `/view_products`
@app.route('/product_database')
def product_database_redirect():
    return redirect(url_for('view_products'))

@app.route('/')
def home():
    return redirect(url_for('login'))

#endregion

#region Carriers

# Route: View and Add Carriers
@app.route('/carriers', methods=['GET', 'POST'])
def manage_carriers():
    if "user_id" not in session:
        flash("You need to log in to access the dashboard.", "warning")
        return redirect(url_for("login"))
    conn = get_db_connection()

    if request.method == 'POST':
        carrier_name = request.form['name']
        if carrier_name:
            try:
                conn.execute('INSERT INTO carriers (name) VALUES (?)', (carrier_name,))
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Prevent duplicate carrier names

    carriers = conn.execute('SELECT * FROM carriers').fetchall()
    conn.close()

    return render_template('carriers.html', carriers=carriers)

# Route: Delete Carrier
@app.route('/delete_carrier/<int:carrier_id>', methods=['POST'])
def delete_carrier(carrier_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM carriers WHERE id = ?', (carrier_id,))
    conn.commit()
    conn.close()
    return redirect('/carriers')

#endregion

#region Customers

# Route: Add Customer
@app.route("/add_customer", methods=["POST"])
def add_customer():
    name = request.form["name"]
    address = request.form["address"]
    category = request.form["category"]

    # Connect to the database and insert a new customer
    conn = get_db_connection()
    conn.execute("INSERT INTO customers (name, address, category) VALUES (?, ?, ?)",
                 (name, address, category))
    conn.commit()
    conn.close()

    flash("Customer added successfully!", "success")
    return redirect(url_for("customers"))  # Corrected to redirect to customers page

# Route: Display all Customers
@app.route("/customers")
def customers():
    conn = get_db_connection()
    customers = conn.execute("SELECT * FROM customers").fetchall()
    conn.close()

    return render_template("customers.html", customers=customers)  # Corrected to render customers.html

# Route: Edit Customer
@app.route("/edit_customer/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    conn = get_db_connection()
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()

    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        category = request.form["category"]

        conn.execute("""
            UPDATE customers 
            SET name = ?, address = ?, category = ? 
            WHERE id = ?
        """, (name, address, category, customer_id))
        conn.commit()
        conn.close()

        flash("Customer updated successfully!", "success")
        return redirect(url_for("customers"))  # Corrected to redirect to customers page

    conn.close()
    return render_template("edit_customer.html", customer=customer)

# Route: Delete Customer
@app.route("/delete_customer/<int:customer_id>")
def delete_customer(customer_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()

    flash("Customer deleted successfully.", "success")
    return redirect(url_for("customers"))  # Corrected to redirect to customers page


#endregion

#region Products

# Route: Product Management
@app.route('/view_products', methods=['GET', 'POST'])
def view_products():
    conn = get_db_connection()

    # Handle POST (Adding products)
    if request.method == 'POST':
        product_name = request.form['product_name']
        product_weight = float(request.form['product_weight'])
        weight_type = request.form['weight_type']
        supplier = request.form['supplier']
        price = float(request.form['price'])

        try:
            conn.execute(
                'INSERT INTO products (product_name, product_weight, weight_type, supplier, price) VALUES (?, ?, ?, ?, ?)',
                (product_name, product_weight, weight_type, supplier, price)
            )
            conn.commit()
            flash("Product added successfully!", "success")
        except sqlite3.IntegrityError:
            flash("Failed to add product. Duplicate entry or invalid data.", "danger")

    # Fetch products (search or all)
    search_query = request.args.get('search', '').strip()
    if search_query:
        query = "SELECT * FROM products WHERE product_name LIKE ?"
        params = [f"%{search_query}%"]
    else:
        query = "SELECT * FROM products"
        params = []

    products = conn.execute(query, params).fetchall()
    total_records = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()

    return render_template(
        'product_database.html',
        products=products,
        search_query=search_query,
        total_records=total_records
    )
@app.route('/edit_product', methods=['POST'])
def edit_product():
    product_id = request.form['product_id']
    product_name = request.form['product_name']
    product_weight = request.form['product_weight']
    weight_type = request.form['weight_type']
    supplier = request.form['supplier']
    price = request.form['price']

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE products
        SET product_name = ?, product_weight = ?, weight_type = ?, supplier = ?, price = ?
        WHERE product_id = ?
        """,
        (product_name, product_weight, weight_type, supplier, price, product_id)
    )
    conn.commit()
    conn.close()

    flash("Product updated successfully!", "success")
    return redirect(url_for('view_products'))  # Redirect back to the product database page



@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM products WHERE "Product ID" = ?', (product_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting product: {e}")
        return jsonify({"success": False, "error": str(e)})



@app.route('/add_product', methods=['POST'])
def add_product():
    product_name = request.form['product_name']
    product_weight = float(request.form['product_weight'])  # Allow decimals
    weight_type = request.form['weight_type']
    supplier = request.form['supplier']
    price = float(request.form['price'])  # Allow decimals

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO products (product_name, product_weight, weight_type, supplier, price) VALUES (?, ?, ?, ?, ?)',
        (product_name, product_weight, weight_type, supplier, price)
    )
    conn.commit()
    conn.close()

    flash("Product added successfully!", "success")
    return redirect(url_for('view_products'))


#endregion

#region Miscellaneous

@app.route('/list_of_html_files')
def list_of_html_files():
    # Get the list of HTML files in the 'templates' directory
    html_files = [f[:-5] for f in os.listdir('templates') if f.endswith('.html')]  # Strip '.html'

    # Render the index page and pass the html_files list
    return render_template('list_of_html_files.html', html_files=html_files)

@app.route('/<page>')
def render_page(page):
    try:
        # Try to render the requested HTML file with the '.html' extension added back
        return render_template(f"{page}.html")
    except Exception as e:
        return f"Error: {str(e)}", 404




#endregion

#region Template for showing records

@app.route('/record_template', methods=['GET', 'POST'])
def template_manage_records():
    conn = get_db_connection()

    # Handle POST method (adding records)
    if request.method == 'POST':
        record_name = request.form['record_name']
        description = request.form['description']
        category = request.form['category']
        status = request.form['status']

        try:
            conn.execute('INSERT INTO test_records (record_name, description, category, status) VALUES (?, ?, ?, ?)',
                         (record_name, description, category, status))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Handle duplicate errors if necessary

    # Always fetch all records if search query is empty or not provided
    search_query = request.args.get('search', '').strip()  # Strip whitespace for consistency
    if search_query:
        query = "SELECT * FROM test_records WHERE record_name LIKE ?"
        params = [f"%{search_query}%"]
    else:
        query = "SELECT * FROM test_records"  # Fetch all records if no search term
        params = []

    records = conn.execute(query, params).fetchall()
    total_records = conn.execute("SELECT COUNT(*) FROM test_records").fetchone()[0]
    filtered_count = len(records)

    conn.close()

    # Render template with records, search query, and counts
    return render_template(
        'record_template.html',
        records=records,
        search_query=search_query,
        filtered_count=filtered_count,
        total_records=total_records
    )






@app.route('/template_add_record', methods=['GET', 'POST'])
def template_add_record():
    if request.method == 'POST':
        record_name = request.form['record_name']
        description = request.form['description']
        category = request.form['category']
        status = request.form['status']


        conn = get_db_connection()
        conn.execute(
            'INSERT INTO test_records (record_name, description, category, status) VALUES (?, ?, ?, ?)',
            (record_name, description, category, status)
        )
        conn.commit()
        conn.close()



    return jsonify({"success": True})


@app.route('/template_edit_record', methods=['POST'])
def template_edit_record():
    record_id = request.form['record_id']
    record_name = request.form['record_name']
    description = request.form['description']
    category = request.form['category']
    status = request.form['status']

    conn = get_db_connection()
    conn.execute(
        'UPDATE test_records SET record_name = ?, description = ?, category = ?, status = ? WHERE record_id = ?',
        (record_name, description, category, status, record_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})


@app.route('/template_delete_record/<int:record_id>', methods=['POST'])
def template_delete_record(record_id):
    conn = get_db_connection()

    # Delete the record by ID
    conn.execute('DELETE FROM test_records WHERE record_id = ?', (record_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})
print(app.url_map)


#endregion for

#region Customer Accounts
@app.route("/create_customer_account", methods=["GET", "POST"])
def create_customer_account():
    if request.method == "POST":
        clinic_name = request.form["clinic_name"]
        clinic_address = request.form["clinic_address"]
        clinic_username = request.form["clinic_username"]
        clinic_password = request.form["clinic_password"]
        clinic_category = request.form["clinic_category"]
        preferred_carrier = request.form.get("preferred_carrier")  # Capture preferred carrier

        hashed_password = generate_password_hash(clinic_password)

        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO customer_account (
                    clinic_name, clinic_address, clinic_username, clinic_password, clinic_category, preferred_carrier
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (clinic_name, clinic_address, clinic_username, hashed_password, clinic_category, preferred_carrier))
            conn.commit()
            flash("Customer account created successfully!", "success")
            return redirect(url_for("customer_login"))
        except sqlite3.IntegrityError:
            flash("Clinic username already exists. Please choose a different one.", "danger")
        finally:
            conn.close()

    conn = get_db_connection()
    carriers = conn.execute("SELECT name FROM carriers").fetchall()  # Fetch carriers
    conn.close()

    return render_template("create_customer_account.html", carriers=carriers)


#endregion

#region Customer Menu

@app.route("/customer_menu")
def customer_menu():
    # Check if the user is logged in and is a customer
    if "customer_id" not in session or session.get("user_role") != "customer":
        flash("You need to log in as a customer to access this page.", "danger")
        return redirect(url_for("login"))

    return render_template("customer_menu.html")


#endregion

#region Item Information and Stock

@app.route('/item_information', methods=['GET'])
def item_information():
    search_query = request.args.get('search', '').strip()

    conn = get_db_connection()
    if search_query:
        query = """
            SELECT p.product_id, p.product_name, p.product_weight, p.weight_type,
                   ps.stock_location, ps.total_quantity, ps.primary_quantity
            FROM products p
            LEFT JOIN product_stock ps ON p.product_id = ps.product_id
            WHERE p.product_name LIKE ?
        """
        params = [f"%{search_query}%"]
    else:
        query = """
            SELECT p.product_id, p.product_name, p.product_weight, p.weight_type,
                   ps.stock_location, ps.total_quantity, ps.primary_quantity
            FROM products p
            LEFT JOIN product_stock ps ON p.product_id = ps.product_id
        """
        params = []

    items = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('item_information.html', items=items, search_query=search_query)



@app.route('/get_product_details/<int:product_id>', methods=['GET'])
def get_product_details(product_id):
    conn = get_db_connection()

    # Check if the current user is an admin
    is_admin = session.get('user_role') == 'Admin'

    # Fetch product information from the `products` table
    product = conn.execute('SELECT * FROM products WHERE product_id = ?', (product_id,)).fetchone()

    # Fetch stock information from the `product_stock` table
    stock = conn.execute('SELECT * FROM product_stock WHERE product_id = ?', (product_id,)).fetchone()
    conn.close()

    if not product:
        return jsonify({"error": "Product not found", "is_admin": is_admin}), 404

    # Combine product and stock data for the response
    details = {
        "is_admin": is_admin,  # Include admin status in the response
        "product_id": product["product_id"],
        "product_name": product["product_name"],
        "product_weight": f"{product['product_weight']} {product['weight_type']}",
        "supplier": product["supplier"],
        "price": product["price"],
        "total_quantity": stock["total_quantity"] if stock else "N/A",
        "primary_quantity": stock["primary_quantity"] if stock else "N/A",
        "stock_location": stock["stock_location"] if stock else "N/A",
        "primary_capacity": stock["primary_capacity"] if stock else "N/A",
        "barcode": stock["barcode"] if stock else "N/A",
    }

    return jsonify(details)



@app.route('/item_details/<int:product_id>', methods=['GET'])
def get_item_details(product_id):
    conn = get_db_connection()

    # Fetch product details
    product = conn.execute('SELECT * FROM products WHERE "Product ID" = ?', (product_id,)).fetchone()

    # Fetch stock details
    stock = conn.execute('SELECT * FROM product_stock WHERE product_id = ?', (product_id,)).fetchone()
    conn.close()

    if not product:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify({
        'product': {
            'Product ID': product['Product ID'],
            'Product Name': product['Product Name'],
            'Product Weight': f"{product['Product Weight']} {product['Weight Type']}",
            'Supplier': product['Supplier'],
            'Price': product['Price'],
        },
        'stock': stock or {}
    })


from sqlite3 import IntegrityError


@app.route('/update_stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    data = request.json
    conn = get_db_connection()

    try:
        # Check if the stock entry exists
        stock = conn.execute('SELECT * FROM product_stock WHERE product_id = ?', (product_id,)).fetchone()

        if stock:
            # Update existing stock record
            conn.execute('''
                UPDATE product_stock
                SET total_quantity = ?, primary_quantity = ?, stock_location = ?, primary_capacity = ?, barcode = ?
                WHERE product_id = ?
            ''', (data['total_quantity'], data['primary_quantity'], data['stock_location'], data['primary_capacity'],
                  data['barcode'], product_id))
        else:
            # Insert new stock record
            conn.execute('''
                INSERT INTO product_stock (product_id, total_quantity, primary_quantity, stock_location, primary_capacity, barcode)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (product_id, data['total_quantity'], data['primary_quantity'], data['stock_location'],
                  data['primary_capacity'], data['barcode']))

        conn.commit()
        conn.close()
        return jsonify({'success': True})

    except IntegrityError as e:
        conn.close()
        if 'UNIQUE constraint failed' in str(e):
            return jsonify({'success': False, 'error': 'Duplicate value detected for Stock Location or Barcode.'})
        return jsonify({'success': False, 'error': 'Database error occurred.'})


#endregion

#region Customer Ordering

@app.route("/customer_ordering", methods=["GET"])
def customer_ordering():
    if "customer_id" not in session or session.get("user_role") != "customer":
        flash("You need to log in as a customer to access this page.", "danger")
        return redirect(url_for("customer_login"))
    return render_template("customer_ordering.html")


# Search for products
@app.route('/search_products', methods=['GET'])
def search_products():
    query = request.args.get('query', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    # Use SQL LIKE query to find products matching the search
    cursor.execute("SELECT product_id, product_name, price FROM products WHERE product_name LIKE ?", (f"%{query}%",))
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)


# Add item to cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.json
    product_id = data['product_id']
    quantity = int(data['quantity'])

    conn = get_db_connection()
    cursor = conn.cursor()
    product = cursor.execute("SELECT product_name, price FROM products WHERE product_id = ?", (product_id,)).fetchone()
    conn.close()

    if product:
        product_name, price = product
        item = {
            "product_id": product_id,
            "product_name": product_name,
            "quantity": quantity,
            "price": price,
            "total_price": price * quantity
        }
        return jsonify(item)
    return jsonify({"error": "Product not found"}), 404

# Submit order
@app.route('/submit_order', methods=['POST'])
def submit_order():
    data = request.json
    clinic_id = session.get('customer_id')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the clinic information and category from customer_account
    clinic = cursor.execute("""
        SELECT clinic_name, clinic_address, clinic_category, preferred_carrier 
        FROM customer_account 
        WHERE id = ?
    """, (clinic_id,)).fetchone()

    if not clinic:
        return jsonify({"error": "Customer account not found"}), 404

    clinic_name, clinic_address, clinic_category, preferred_carrier = clinic
    cart = data['cart']

    total_quantity = sum(item['quantity'] for item in cart)
    lines = len(cart)

    # Ensure the category matches the customer's clinic_category
    category = clinic_category

    description = data.get('description', '')


    # Determine order status based on the urgent flag (if urgent, override default status)
    is_urgent = data.get('urgent', False)
    order_status = "urgent" if is_urgent else "new"

    # Insert the order with the appropriate status
    cursor.execute("""
        INSERT INTO orders (
            clinic_name, clinic_address, description, category, status, quantity, lines, finalized_time, order_confirmed, carrier
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        clinic_name,
        clinic_address,
        description,
        category,  # Use the clinic's category
        order_status,  # Use "urgent" if urgent flag is true, otherwise "new"
        total_quantity,
        lines,
        datetime.now(),
        "Pending",  # Default for order_confirmed
        preferred_carrier
    ))

    # Get the order_id of the newly inserted order
    order_id = cursor.lastrowid

    # Insert items into the order_items table
    for item in cart:
        cursor.execute("""
            INSERT INTO order_items (order_id, item_name, quantity)
            VALUES (?, ?, ?)
        """, (order_id, item['productName'], item['quantity']))

    conn.commit()
    conn.close()

    return jsonify({"message": "Order submitted successfully!", "order_id": order_id})


#endregion

#region Edit Customer Account

@app.route('/get_customer_details', methods=['GET'])
def get_customer_details():
    if "customer_id" not in session:
        return jsonify({"error": "You need to log in to access this page."}), 403

    customer_id = session['customer_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    customer = cursor.execute("""
        SELECT clinic_name, clinic_address, clinic_category, priority_customer 
        FROM customer_account 
        WHERE id = ?
    """, (customer_id,)).fetchone()

    conn.close()

    if customer:
        return jsonify({
            "clinic_name": customer[0],
            "clinic_address": customer[1],
            "clinic_category": customer[2],
            "priority_customer": bool(customer[3])  # Convert to boolean
        })
    return jsonify({"error": "Customer not found."}), 404


@app.route("/edit_customer_account", methods=["GET", "POST"])
def edit_customer_account():
    # Ensure a customer is logged in
    if "customer_id" not in session:
        flash("You need to log in as a customer to access this page.", "danger")
        return redirect(url_for("customer_login"))

    customer_id = session["customer_id"]
    conn = get_db_connection()

    if request.method == "POST":
        # Get JSON data from the request
        data = request.get_json()
        clinic_name = data.get("clinic_name")
        clinic_address = data.get("clinic_address")
        clinic_category = data.get("clinic_category")
        clinic_password = data.get("clinic_password", "").strip()
        preferred_carrier = data.get("preferred_carrier")
        priority_customer = data.get("priority_customer", False)

        if clinic_password:
            hashed_password = generate_password_hash(clinic_password)
            conn.execute("""
                UPDATE customer_account
                SET clinic_name = ?, clinic_address = ?, clinic_category = ?, clinic_password = ?,
                    preferred_carrier = ?, priority_customer = ?
                WHERE id = ?
            """, (clinic_name, clinic_address, clinic_category, hashed_password,
                  preferred_carrier, int(priority_customer), customer_id))
        else:
            conn.execute("""
                UPDATE customer_account
                SET clinic_name = ?, clinic_address = ?, clinic_category = ?,
                    preferred_carrier = ?, priority_customer = ?
                WHERE id = ?
            """, (clinic_name, clinic_address, clinic_category, preferred_carrier, int(priority_customer), customer_id))
        conn.commit()
        conn.close()
        return jsonify({"message": "Customer account updated successfully!"})

    else:
        customer_row = conn.execute("SELECT * FROM customer_account WHERE id = ?", (customer_id,)).fetchone()
        if not customer_row:
            conn.close()
            flash("Customer not found.", "danger")
            return redirect(url_for("customer_menu"))
        customer = dict(customer_row)
        # Convert each carrier (Row object) into a dictionary
        carriers = [dict(row) for row in conn.execute("SELECT id, name FROM carriers").fetchall()]
        print("DEBUG: Found", len(carriers), "carriers")
        conn.close()
        return render_template("edit_customer_account.html", customer=customer, carriers=carriers)


@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    print("Request received at /update_order_status")
    data = request.json
    order_id = data.get('order_id')
    new_status = data.get('status')

    if not order_id or not new_status:
        return jsonify({"error": "Missing order_id or status in the request."}), 400

    valid_statuses = ['new', 'old', 'priority', 'urgent']
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status '{new_status}' provided."}), 400

    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE orders SET status = ? WHERE order_id = ?',
            (new_status, order_id)
        )
        conn.commit()
        return jsonify({"message": f"Order status updated to '{new_status}' successfully."})
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()





@app.route('/update_order', methods=['POST'])
def update_order():
    data = request.json
    print(f"Received data in /update_order: {data}")  # Debugging log

    order_id = data.get('order_id')
    new_category = data.get('category')

    # Validate inputs
    if not order_id or not new_category:
        print("Error: Missing order_id or category")  # Debugging log
        return jsonify({'error': 'Missing order_id or category in the request.'}), 400

    valid_categories = ['new', 'old', 'priority', 'urgent', 'unallocated', 'misc', 'on_hold', 'pick-ups', 'Van', '9:30', '11:30', '1:30', '3:30', '5:30']
    if new_category not in valid_categories:
        print(f"Invalid category '{new_category}'")  # Debugging log
        return jsonify({'error': f"Invalid category '{new_category}'. Must be one of {valid_categories}."}), 400

    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE orders SET category = ? WHERE order_id = ?',
            (new_category, order_id)
        )
        conn.commit()
        print(f"Order {order_id} updated to category '{new_category}'")  # Debugging log
        return jsonify({'success': True, 'message': f"Order {order_id} updated to category '{new_category}'."})
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")  # Debugging log
        return jsonify({'error': f"Database error: {str(e)}"}), 500
    finally:
        conn.close()



#endregion

#region Order Confirmation

@app.route('/get_pending_orders', methods=['GET'])
def get_pending_orders():
    if "user_id" not in session or session.get("user_role") != "Admin":
        return jsonify({"error": "Access restricted to admins only."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch pending orders and calculate total_price dynamically
    pending_orders = cursor.execute("""
        SELECT 
            o.order_id, 
            o.clinic_name, 
            o.clinic_address, 
            o.category, 
            o.lines, 
            o.quantity, 
            o.finalized_time,
            SUM(oi.quantity * p.price) AS total_price
        FROM orders o
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN products p ON oi.item_name = p.product_name
        WHERE o.order_confirmed = 'Pending'
        GROUP BY o.order_id
        ORDER BY o.finalized_time DESC
    """).fetchall()

    conn.close()

    # Convert rows to a list of dictionaries
    orders = [dict(row) for row in pending_orders]
    return jsonify(orders)

@app.route('/confirm_order')
def confirm_order_page():
    if "user_id" not in session or session.get("user_role") != "Admin":
        flash("Access restricted to admins only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    pending_orders = conn.execute("""
        SELECT 
            o.order_id, 
            o.clinic_name, 
            o.category, 
            o.lines, 
            o.quantity, 
            SUM(oi.quantity * p.price) AS total_price
        FROM orders o
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN products p ON oi.item_name = p.product_name
        WHERE o.order_confirmed = 'Pending'
        GROUP BY o.order_id
        ORDER BY o.finalized_time DESC
    """).fetchall()
    conn.close()

    print(pending_orders)  # Debugging: Check the data

    # Convert rows to dictionaries for Jinja2 rendering
    orders = [dict(order) for order in pending_orders]
    print(orders)  # Debugging: Ensure orders is a list of dictionaries

    return render_template("confirm_order.html", orders=orders)



@app.route('/confirm_order_status', methods=['POST'])
def confirm_order_status():
    print("Request received at /confirm_order_status")
    if "user_id" not in session or session.get("user_role") != "Admin":
        return jsonify({"error": "Access restricted to admins only."}), 403

    data = request.json
    print(f"Received data in /confirm_order_status: {data}")  # Debugging log
    order_id = data.get('order_id')
    new_confirmation_status = data.get('status')

    if new_confirmation_status not in ['Confirmed', 'Rejected']:
        print(f"Invalid confirmation status: {new_confirmation_status}")  # Debugging log
        return jsonify({"error": "Invalid confirmation status."}), 400

    conn = get_db_connection()
    # Query for the admin's username using the current user ID
    admin = conn.execute("SELECT username FROM users WHERE id = ?", (session.get("user_id"),)).fetchone()
    finalized_by = admin["username"] if admin else "Unknown"

    try:
        # Update the order's confirmation status and set finalized_by to the admin's username
        conn.execute("""
            UPDATE orders
            SET order_confirmed = ?, finalized_by = ?
            WHERE order_id = ?
        """, (new_confirmation_status, finalized_by, order_id))
        conn.commit()
        return jsonify({"message": f"Order {order_id} has been {new_confirmation_status.lower()}."})
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()



#endregion

#region Keep at bottom of app!!

if __name__ == '__main__':
    init_db()

    app.run(host='0.0.0.0', port=5000, debug=True)


#endregion
































