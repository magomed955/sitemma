from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "ironcage_secret_2025"
DB = "database.db"
ADMIN_PASSWORD = "Mutsulkhanov67200"
UPLOAD_FOLDER = os.path.join("static", "img")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS fighters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        categorie TEXT NOT NULL,
        victoires INTEGER DEFAULT 0,
        defaites INTEGER DEFAULT 0,
        nuls INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        img TEXT DEFAULT 'default.jpg'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS fights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fighter1_id INTEGER,
        fighter2_id INTEGER,
        date TEXT,
        lieu TEXT,
        categorie TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fight_id INTEGER,
        gagnant_id INTEGER,
        methode TEXT,
        nom1 TEXT,
        nom2 TEXT,
        date TEXT
    )''')
    # Ajouter colonne results si elle n'existe pas (migration)
    try:
        c.execute("ALTER TABLE results ADD COLUMN nom1 TEXT")
        c.execute("ALTER TABLE results ADD COLUMN nom2 TEXT")
        c.execute("ALTER TABLE results ADD COLUMN date TEXT")
    except:
        pass

    c.execute("SELECT COUNT(*) FROM fighters")
    if c.fetchone()[0] == 0:
        fighters = [
            ("Bakhalaev", "Poids Lourd", 10, 1, 0, 1100, "bakhalaev.jpg"),
            ("Marc Dupont", "Poids Léger", 9, 4, 1, 950, "default.jpg"),
            ("Kevin Torres", "Poids Léger", 7, 3, 0, 800, "default.jpg"),
            ("Julien Bernard", "Poids Welter", 15, 1, 0, 1500, "default.jpg"),
            ("Ahmed Rais", "Poids Welter", 11, 3, 0, 1100, "default.jpg"),
            ("Thomas Klein", "Poids Welter", 8, 5, 0, 780, "default.jpg"),
            ("Ryo Tanaka", "Poids Moyen", 10, 2, 1, 1050, "default.jpg"),
            ("Igor Petrov", "Poids Moyen", 8, 4, 0, 870, "default.jpg"),
            ("Luis Herrera", "Poids Lourd", 18, 3, 0, 1800, "default.jpg"),
            ("Bjorn Hansen", "Poids Lourd", 14, 5, 1, 1350, "default.jpg"),
        ]
        c.executemany("INSERT INTO fighters (nom, categorie, victoires, defaites, nuls, points, img) VALUES (?,?,?,?,?,?,?)", fighters)

        def get_id(name):
            row = c.execute("SELECT id FROM fighters WHERE nom=?", (name,)).fetchone()
            return row["id"] if row else None

        fights = [
            (get_id("Marc Dupont"), get_id("Julien Bernard"), "2025-06-14", "Paris Arena", "Poids Welter"),
            (get_id("Ahmed Rais"), get_id("Thomas Klein"), "2025-06-14", "Paris Arena", "Poids Welter"),
            (get_id("Ryo Tanaka"), get_id("Igor Petrov"), "2025-07-05", "Lyon Dome", "Poids Moyen"),
        ]
        c.executemany("INSERT INTO fights (fighter1_id, fighter2_id, date, lieu, categorie) VALUES (?,?,?,?,?)", fights)

    conn.commit()
    conn.close()

# ── AUTH ──────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated

# ── ROUTES PUBLIQUES ──────────────────────────────────────

@app.route("/")
def index():
    conn = get_db()
    fights = conn.execute("""
        SELECT f.*, f1.nom as nom1, f2.nom as nom2
        FROM fights f
        JOIN fighters f1 ON f.fighter1_id = f1.id
        JOIN fighters f2 ON f.fighter2_id = f2.id
        ORDER BY f.date ASC LIMIT 3
    """).fetchall()
    conn.close()
    return render_template("index.html", fights=fights)

@app.route("/combats")
def combats():
    conn = get_db()
    fights = conn.execute("""
        SELECT f.*,
               f1.nom as nom1, f2.nom as nom2,
               f1.victoires as v1, f1.defaites as d1,
               f2.victoires as v2, f2.defaites as d2,
               f1.img as img1, f2.img as img2
        FROM fights f
        JOIN fighters f1 ON f.fighter1_id = f1.id
        JOIN fighters f2 ON f.fighter2_id = f2.id
        ORDER BY f.date ASC
    """).fetchall()
    conn.close()
    return render_template("combats.html", fights=fights)

@app.route("/classements")
def classements():
    conn = get_db()
    categories = ["Poids Léger", "Poids Welter", "Poids Moyen", "Poids Lourd"]
    data = {}
    for cat in categories:
        data[cat] = conn.execute(
            "SELECT * FROM fighters WHERE categorie=? ORDER BY points DESC", (cat,)
        ).fetchall()
    conn.close()
    return render_template("classements.html", data=data)

@app.route("/fighter/<int:id>")
def fighter_profile(id):
    conn = get_db()
    fighter = conn.execute("SELECT * FROM fighters WHERE id=?", (id,)).fetchone()
    history = conn.execute("""
        SELECT r.*, f1.nom as nom1, f2.nom as nom2, f3.nom as gagnant_nom
        FROM results r
        JOIN fighters f1 ON f1.id = r.gagnant_id
        LEFT JOIN fighters f2 ON f2.id != r.gagnant_id
        JOIN fighters f3 ON f3.id = r.gagnant_id
        WHERE r.nom1 = ? OR r.nom2 = ?
        ORDER BY r.id DESC
    """, (fighter["nom"], fighter["nom"])).fetchall() if fighter else []
    conn.close()
    if not fighter:
        return redirect("/classements")
    return render_template("fighter.html", fighter=fighter, history=history)

@app.route("/resultats")
def resultats():
    conn = get_db()
    results = conn.execute("""
        SELECT r.*, fi.nom as gagnant_nom, fi.img as gagnant_img
        FROM results r
        JOIN fighters fi ON r.gagnant_id = fi.id
        ORDER BY r.id DESC
    """).fetchall()
    conn.close()
    return render_template("resultats.html", results=results)

# ── ADMIN AUTH ────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        flash("Mot de passe incorrect")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin/login")

# ── ADMIN DASHBOARD ───────────────────────────────────────

@app.route("/admin")
@admin_required
def admin():
    conn = get_db()
    fighters = conn.execute("SELECT * FROM fighters ORDER BY categorie, points DESC").fetchall()
    fights = conn.execute("""
        SELECT f.*, f1.nom as nom1, f2.nom as nom2
        FROM fights f
        JOIN fighters f1 ON f.fighter1_id = f1.id
        JOIN fighters f2 ON f.fighter2_id = f2.id
        ORDER BY f.date ASC
    """).fetchall()
    results = conn.execute("""
        SELECT r.*, fi.nom as gagnant_nom
        FROM results r
        JOIN fighters fi ON r.gagnant_id = fi.id
        ORDER BY r.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin.html", fighters=fighters, fights=fights, results=results)

# ── ADMIN COMBATTANTS ─────────────────────────────────────

@app.route("/admin/fighter/add", methods=["POST"])
@admin_required
def add_fighter():
    img_filename = "default.jpg"
    if "img" in request.files:
        file = request.files["img"]
        if file and file.filename and allowed_file(file.filename):
            img_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], img_filename))

    conn = get_db()
    conn.execute(
        "INSERT INTO fighters (nom, categorie, victoires, defaites, nuls, points, img) VALUES (?,?,?,?,?,?,?)",
        (request.form["nom"], request.form["categorie"],
         int(request.form.get("victoires", 0)), int(request.form.get("defaites", 0)),
         int(request.form.get("nuls", 0)), int(request.form.get("points", 0)),
         img_filename)
    )
    conn.commit()
    conn.close()
    flash("Combattant ajouté.")
    return redirect("/admin")

@app.route("/admin/fighter/edit/<int:id>", methods=["POST"])
@admin_required
def edit_fighter(id):
    conn = get_db()
    current = conn.execute("SELECT img FROM fighters WHERE id=?", (id,)).fetchone()
    img_filename = current["img"] if current else "default.jpg"

    if "img" in request.files:
        file = request.files["img"]
        if file and file.filename and allowed_file(file.filename):
            img_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], img_filename))

    conn.execute(
        "UPDATE fighters SET nom=?, categorie=?, victoires=?, defaites=?, nuls=?, points=?, img=? WHERE id=?",
        (request.form["nom"], request.form["categorie"],
         int(request.form.get("victoires", 0)), int(request.form.get("defaites", 0)),
         int(request.form.get("nuls", 0)), int(request.form.get("points", 0)),
         img_filename, id)
    )
    conn.commit()
    conn.close()
    flash("Combattant mis à jour.")
    return redirect("/admin")

@app.route("/admin/fighter/delete/<int:id>")
@admin_required
def delete_fighter(id):
    conn = get_db()
    conn.execute("DELETE FROM fighters WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Combattant supprimé.")
    return redirect("/admin")

# ── ADMIN COMBATS ─────────────────────────────────────────

@app.route("/admin/fight/add", methods=["POST"])
@admin_required
def add_fight():
    conn = get_db()
    conn.execute(
        "INSERT INTO fights (fighter1_id, fighter2_id, date, lieu, categorie) VALUES (?,?,?,?,?)",
        (int(request.form["fighter1_id"]), int(request.form["fighter2_id"]),
         request.form["date"], request.form["lieu"], request.form["categorie"])
    )
    conn.commit()
    conn.close()
    flash("Combat ajouté.")
    return redirect("/admin")

@app.route("/admin/fight/delete/<int:id>")
@admin_required
def delete_fight(id):
    conn = get_db()
    conn.execute("DELETE FROM fights WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Combat supprimé.")
    return redirect("/admin")

# ── ADMIN RÉSULTATS ───────────────────────────────────────

@app.route("/admin/result/add", methods=["POST"])
@admin_required
def add_result():
    fight_id   = int(request.form["fight_id"])
    gagnant_id = int(request.form["gagnant_id"])
    methode    = request.form["methode"]

    conn = get_db()
    fight = conn.execute("SELECT * FROM fights WHERE id=?", (fight_id,)).fetchone()

    if fight:
        perdant_id = fight["fighter2_id"] if gagnant_id == fight["fighter1_id"] else fight["fighter1_id"]
        f1 = conn.execute("SELECT nom FROM fighters WHERE id=?", (fight["fighter1_id"],)).fetchone()
        f2 = conn.execute("SELECT nom FROM fighters WHERE id=?", (fight["fighter2_id"],)).fetchone()

        conn.execute(
            "INSERT INTO results (fight_id, gagnant_id, methode, nom1, nom2, date) VALUES (?,?,?,?,?,?)",
            (fight_id, gagnant_id, methode,
             f1["nom"] if f1 else "", f2["nom"] if f2 else "", fight["date"])
        )
        conn.execute("UPDATE fighters SET victoires = victoires + 1, points = points + 100 WHERE id=?", (gagnant_id,))
        conn.execute("UPDATE fighters SET defaites = defaites + 1 WHERE id=?", (perdant_id,))
        conn.execute("DELETE FROM fights WHERE id=?", (fight_id,))
        conn.commit()
        flash("Résultat enregistré.")
    else:
        flash("Combat introuvable.")

    conn.close()
    return redirect("/admin")

@app.route("/admin/result/delete/<int:id>")
@admin_required
def delete_result(id):
    conn = get_db()
    conn.execute("DELETE FROM results WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Résultat supprimé.")
    return redirect("/admin")

# ── MAIN ──────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
