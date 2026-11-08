import os, re, sqlite3, secrets, uuid, math
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("LEDGERLINE_DB", os.path.join(BASE_DIR, "ledgerline.db"))
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-this-demo-secret-before-deployment")

app = Flask(__name__)
app.config.update(JWT_SECRET_KEY=SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=8))
CORS(app, resources={r"/api/*": {"origins": os.environ.get("FRONTEND_ORIGINS", "*").split(",")}})
jwt = JWTManager(app)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def audit(user_id, action, decision, details="", entity_type=None, entity_id=None):
    db = get_db()
    db.execute("""INSERT INTO audit_logs
        (user_id, action, decision, details, entity_type, entity_id, ip_address, user_agent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, action, decision, details, entity_type, entity_id,
         request.remote_addr, request.headers.get("User-Agent", "")[:250], now_iso()))
    db.commit()


def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('user','admin')),
      balance_cents INTEGER NOT NULL DEFAULT 100000 CHECK(balance_cents >= 0),
      account_number TEXT NOT NULL UNIQUE,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS transactions (
      id TEXT PRIMARY KEY,
      sender_id INTEGER NOT NULL REFERENCES users(id),
      recipient_id INTEGER NOT NULL REFERENCES users(id),
      amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
      status TEXT NOT NULL CHECK(status IN ('completed','failed')),
      description TEXT,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER REFERENCES users(id),
      action TEXT NOT NULL,
      decision TEXT NOT NULL CHECK(decision IN ('ALLOWED','DENIED')),
      details TEXT NOT NULL,
      entity_type TEXT,
      entity_id TEXT,
      ip_address TEXT,
      user_agent TEXT,
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender_id);
    CREATE INDEX IF NOT EXISTS idx_transactions_recipient ON transactions(recipient_id);
    CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
    """)
    db.commit()

    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed = [
            ("Aarav Sharma", "aarav@ledgerline.demo", "Demo@1234", "user", 125000, "LL10000001"),
            ("Maya Patel", "maya@ledgerline.demo", "Demo@1234", "user", 85000, "LL10000002"),
            ("Admin User", "admin@ledgerline.demo", "Admin@1234", "admin", 500000, "LL10000000")
        ]
        for name, email, password, role, cents, account in seed:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            db.execute("INSERT INTO users (name,email,password_hash,role,balance_cents,account_number,created_at) VALUES (?,?,?,?,?,?,?)",
                       (name, email.lower(), hashed, role, cents, account, now_iso()))
        db.commit()


def json_error(message, status=400):
    return jsonify({"error": message}), status


def clean_email(value):
    return (value or "").strip().lower()


def clean_name(value):
    return " ".join((value or "").strip().split())


def current_user():
    uid = int(get_jwt_identity())
    row = get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return row


@jwt.unauthorized_loader
def missing_token(_reason):
    return json_error("Authentication required", 401)


@jwt.invalid_token_loader
def invalid_token(_reason):
    return json_error("Invalid authentication token", 401)


@jwt.expired_token_loader
def expired_token(_header, _payload):
    return json_error("Authentication token has expired", 401)


@app.before_request
def prepare():
    get_db()


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = clean_name(data.get("name"))
    email = clean_email(data.get("email"))
    password = data.get("password") or ""
    if len(name) < 2 or len(name) > 80:
        audit(None, "REGISTER", "DENIED", "Invalid name")
        return json_error("Name must be 2–80 characters")
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        audit(None, "REGISTER", "DENIED", f"Invalid email: {email}")
        return json_error("Enter a valid email address")
    if len(password) < 8 or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
        audit(None, "REGISTER", "DENIED", "Password policy not met")
        return json_error("Password needs 8+ characters, one uppercase letter, and one number")
    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        audit(None, "REGISTER", "DENIED", f"Email already exists: {email}")
        return json_error("An account already exists with this email", 409)
    account = "LL" + secrets.randbelow(90000000).__str__().rjust(8, "0")
    while db.execute("SELECT 1 FROM users WHERE account_number=?", (account,)).fetchone():
        account = "LL" + secrets.randbelow(90000000).__str__().rjust(8, "0")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cursor = db.execute("INSERT INTO users(name,email,password_hash,role,balance_cents,account_number,created_at) VALUES(?,?,?,?,100000,?,?)",
                        (name, email, hashed, "user", account, now_iso()))
    db.commit()
    uid = cursor.lastrowid
    audit(uid, "REGISTER", "ALLOWED", f"Created user account {account}", "user", uid)
    token = create_access_token(identity=str(uid))
    return jsonify({"token": token, "user": public_user(db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())}), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = clean_email(data.get("email"))
    password = data.get("password") or ""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    valid = user and bcrypt.checkpw(password.encode(), user["password_hash"].encode())
    if not valid:
        audit(user["id"] if user else None, "LOGIN", "DENIED", f"Failed login for {email}")
        return json_error("Invalid email or password", 401)
    audit(user["id"], "LOGIN", "ALLOWED", "Login successful")
    return jsonify({"token": create_access_token(identity=str(user["id"])), "user": public_user(user)})


def public_user(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"],
            "balanceCents": row["balance_cents"], "accountNumber": row["account_number"]}


@app.get("/api/me")
@jwt_required()
def me():
    return jsonify(public_user(current_user()))


@app.post("/api/auth/logout")
@jwt_required()
def logout():
    user = current_user()
    audit(user["id"], "LOGOUT", "ALLOWED", "Session cleared by user")
    return jsonify({"message": "Signed out"})


@app.get("/api/dashboard")
@jwt_required()
def dashboard():
    user = current_user()
    tx = get_db().execute("""SELECT t.*, sender.name sender_name, sender.account_number sender_account,
      recipient.name recipient_name, recipient.account_number recipient_account
      FROM transactions t JOIN users sender ON sender.id=t.sender_id JOIN users recipient ON recipient.id=t.recipient_id
      WHERE sender_id=? OR recipient_id=? ORDER BY created_at DESC LIMIT 20""", (user["id"], user["id"])).fetchall()
    return jsonify({"user": public_user(user), "transactions": [public_transaction(r, user["id"]) for r in tx]})


@app.get("/api/recipients")
@jwt_required()
def recipients():
    user = current_user()
    rows = get_db().execute("SELECT id,name,email,account_number FROM users WHERE id<>? ORDER BY name", (user["id"],)).fetchall()
    return jsonify([{"id": r["id"], "name": r["name"], "email": r["email"], "accountNumber": r["account_number"]} for r in rows])


@app.post("/api/transfers")
@jwt_required()
def transfer():
    sender = current_user()
    data = request.get_json(silent=True) or {}
    recipient_id = data.get("recipientId")
    try:
        raw_amount = float(data.get("amount") or 0)
        if not math.isfinite(raw_amount):
            raise ValueError("non-finite amount")
        amount = round(raw_amount * 100)
    except (TypeError, ValueError, OverflowError):
        amount = 0
    description = (data.get("description") or "Simulation transfer")[:120]
    db = get_db()
    try:
        recipient_id = int(recipient_id)
    except (TypeError, ValueError):
        audit(sender["id"], "TRANSFER", "DENIED", "Invalid recipient identifier")
        return json_error("Choose a valid recipient", 400)
    recipient = db.execute("SELECT * FROM users WHERE id=?", (recipient_id,)).fetchone()
    if not recipient:
        audit(sender["id"], "TRANSFER", "DENIED", "Recipient does not exist")
        return json_error("Recipient not found", 404)
    if recipient_id == sender["id"]:
        audit(sender["id"], "TRANSFER", "DENIED", "Self-transfer attempt")
        return json_error("You cannot transfer funds to yourself")
    if amount < 1:
        audit(sender["id"], "TRANSFER", "DENIED", "Invalid amount")
        return json_error("Amount must be greater than zero")
    if amount > sender["balance_cents"]:
        audit(sender["id"], "TRANSFER", "DENIED", f"Insufficient funds for {amount} cents")
        return json_error("Insufficient balance", 422)

    txid = "TXN-" + uuid.uuid4().hex[:12].upper()
    try:
        db.execute("BEGIN IMMEDIATE")
        sender_now = db.execute("SELECT balance_cents FROM users WHERE id=?", (sender["id"],)).fetchone()[0]
        if sender_now < amount:
            db.rollback()
            audit(sender["id"], "TRANSFER", "DENIED", "Concurrent insufficient balance")
            return json_error("Insufficient balance", 422)
        db.execute("UPDATE users SET balance_cents=balance_cents-? WHERE id=?", (amount, sender["id"]))
        db.execute("UPDATE users SET balance_cents=balance_cents+? WHERE id=?", (amount, recipient_id))
        db.execute("INSERT INTO transactions(id,sender_id,recipient_id,amount_cents,status,description,created_at) VALUES(?,?,?,?,?,?,?)",
                   (txid, sender["id"], recipient_id, amount, "completed", description, now_iso()))
        db.commit()
        audit(sender["id"], "TRANSFER", "ALLOWED", f"Transferred {amount/100:.2f} to user {recipient_id}", "transaction", txid)
        return jsonify({"message": "Transfer completed", "transactionId": txid}), 201
    except sqlite3.Error as exc:
        db.rollback()
        audit(sender["id"], "TRANSFER", "DENIED", "Database transaction failed")
        app.logger.exception(exc)
        return json_error("Transfer could not be completed", 500)


def public_transaction(row, viewer_id):
    incoming = row["recipient_id"] == viewer_id
    return {"id": row["id"], "type": "credit" if incoming else "debit", "amountCents": row["amount_cents"],
            "status": row["status"], "description": row["description"] or "Simulation transfer",
            "createdAt": row["created_at"], "counterparty": row["recipient_name"] if not incoming else row["sender_name"]}


@app.get("/api/transactions")
@jwt_required()
def transactions():
    user = current_user()
    rows = get_db().execute("""SELECT t.*, sender.name sender_name, sender.account_number sender_account,
      recipient.name recipient_name, recipient.account_number recipient_account FROM transactions t
      JOIN users sender ON sender.id=t.sender_id JOIN users recipient ON recipient.id=t.recipient_id
      WHERE sender_id=? OR recipient_id=? ORDER BY created_at DESC""", (user["id"], user["id"])).fetchall()
    return jsonify([public_transaction(r, user["id"]) for r in rows])


@app.get("/api/transactions/<transaction_id>")
@jwt_required()
def transaction_detail(transaction_id):
    user = current_user()
    row = get_db().execute("""SELECT t.*, sender.name sender_name, sender.account_number sender_account,
      recipient.name recipient_name, recipient.account_number recipient_account FROM transactions t
      JOIN users sender ON sender.id=t.sender_id JOIN users recipient ON recipient.id=t.recipient_id
      WHERE t.id=?""", (transaction_id,)).fetchone()
    if not row:
        audit(user["id"], "VIEW_TRANSACTION", "DENIED", "Transaction not found")
        return json_error("Transaction not found", 404)
    if user["role"] != "admin" and user["id"] not in (row["sender_id"], row["recipient_id"]):
        audit(user["id"], "VIEW_TRANSACTION", "DENIED", "Attempted to view another user's transaction", "transaction", transaction_id)
        return json_error("You are not authorized to view this transaction", 403)
    audit(user["id"], "VIEW_TRANSACTION", "ALLOWED", "Viewed transaction details", "transaction", transaction_id)
    return jsonify({
        "id": row["id"], "senderName": row["sender_name"], "senderAccount": row["sender_account"],
        "recipientName": row["recipient_name"], "recipientAccount": row["recipient_account"],
        "amountCents": row["amount_cents"], "status": row["status"],
        "description": row["description"] or "Simulation transfer", "createdAt": row["created_at"]
    })


@app.get("/api/admin/audit")
@jwt_required()
def audit_list():
    user = current_user()
    if user["role"] != "admin":
        audit(user["id"], "VIEW_AUDIT_LOGS", "DENIED", "Non-admin attempted access")
        return json_error("Administrator role required", 403)
    audit(user["id"], "VIEW_AUDIT_LOGS", "ALLOWED", "Viewed audit logs")
    rows = get_db().execute("""SELECT a.*, u.name user_name, u.email user_email FROM audit_logs a
      LEFT JOIN users u ON u.id=a.user_id ORDER BY a.created_at DESC LIMIT 500""").fetchall()
    return jsonify([{k: r[k] for k in r.keys()} for r in rows])


@app.get("/api/admin/users")
@jwt_required()
def admin_users():
    user = current_user()
    if user["role"] != "admin":
        audit(user["id"], "VIEW_USERS", "DENIED", "Non-admin attempted access")
        return json_error("Administrator role required", 403)
    audit(user["id"], "VIEW_USERS", "ALLOWED", "Viewed users")
    rows = get_db().execute("SELECT id,name,email,role,balance_cents,account_number,created_at FROM users ORDER BY created_at DESC").fetchall()
    return jsonify([{k: r[k] for k in r.keys()} for r in rows])


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "LedgerLine API", "database": "sqlite"})


@app.errorhandler(404)
def not_found(_error):
    return json_error("Resource not found", 404)


@app.errorhandler(500)
def server_error(_error):
    return json_error("Internal server error", 500)


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "0") == "1")
