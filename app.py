from flask import Flask, render_template, request, redirect, session, flash
import psycopg2
import psycopg2.extras
import os
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "ironcage_secret_2025"

@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if not os.path.exists("static/img"):
    os.makedirs("static/img")

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Mutsulkhanov67200")
UPLOAD_FOLDER = os.path.join("static", "img")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS fighters (
        id SERIAL PRIMARY KEY,
        nom TEXT NOT NULL,
        categorie TEXT NOT NULL,
        victoires INTEGER DEFAULT 0,
        defaites INTEGER DEFAULT 0,
        nuls INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        img TEXT DEFAULT 'default.jpg'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS fights (
        id SERIAL PRIMARY KEY,
        fighter1_id INTEGER,
        fighter2_id INTEGER,
        date TEXT,
        lieu TEXT,
        categorie TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id SERIAL PRIMARY KEY,
        fight_id INTEGER,
        gagnant_id INTEGER,
        methode TEXT,
        nom1 TEXT,
        nom2 TEXT,
        date TEXT
    )''')

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

def fetchall_dict(cursor):
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def fetchone_dict(cursor):
    cols = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    return dict(zip(cols, row)) if row else None

# ── ROUTES PUBLIQUES ──────────────────────────────────────

@app.route("/")
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT f.*, f1.nom as nom1, f2.nom as nom2
        FROM fights f
        JOIN fighters f1 ON f.fighter1_id = f1.id
        JOIN fighters f2 ON f.fighter2_id = f2.id
        ORDER BY f.date ASC LIMIT 3
    """)
    fights = fetchall_dict(c)
    conn.close()
    return render_template("index.html", fights=fights)

@app.route("/combats")
def combats():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT f.*,
               f1.nom as nom1, f2.nom as nom2,
               f1.victoires as v1, f1.defaites as d1,
               f2.victoires as v2, f2.defaites as d2,
               f1.img as img1, f2.img as img2
        FROM fights f
        JOIN fighters f1 ON f.fighter1_id = f1.id
        JOIN fighters f2 ON f.fighter2_id = f2.id
        ORDER BY f.date ASC
    """)
    fights = fetchall_dict(c)
    conn.close()
    return render_template("combats.html", fights=fights)

@app.route("/classements")
def classements():
    conn = get_db()
    c = conn.cursor()
    categories = ["Poids Léger", "Poids Welter", "Poids Moyen", "Poids Lourd"]
    data = {}
    for cat in categories:
        c.execute("SELECT * FROM fighters WHERE categorie=%s ORDER BY points DESC", (cat,))
        data[cat] = fetchall_dict(c)
    conn.close()
    return render_template("classements.html", data=data)

@app.route("/resultats")
def resultats():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT r.*, fi.nom as gagnant_nom, fi.img as gagnant_img
        FROM results r
        JOIN fighters fi ON r.gagnant_id = fi.id
        ORDER BY r.id DESC
    """)
    results = fetchall_dict(c)
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
    c = conn.cursor()

    c.execute("SELECT * FROM fighters ORDER BY categorie, points DESC")
    fighters = fetchall_dict(c)

    c.execute("""
        SELECT f.*, f1.nom as nom1, f2.nom as nom2
        FROM fights f
        JOIN fighters f1 ON f.fighter1_id = f1.id
        JOIN fighters f2 ON f.fighter2_id = f2.id
        ORDER BY f.date ASC
    """)
    fights = fetchall_dict(c)

    c.execute("""
        SELECT r.*, fi.nom as gagnant_nom
        FROM results r
        JOIN fighters fi ON r.gagnant_id = fi.id
        ORDER BY r.id DESC
    """)
    results = fetchall_dict(c)

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
    c = conn.cursor()
    c.execute(
        "INSERT INTO fighters (nom, categorie, victoires, defaites, nuls, points, img) VALUES (%s,%s,%s,%s,%s,%s,%s)",
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
    c = conn.cursor()
    c.execute("SELECT img FROM fighters WHERE id=%s", (id,))
    current = fetchone_dict(c)
    img_filename = current["img"] if current else "default.jpg"

    if "img" in request.files:
        file = request.files["img"]
        if file and file.filename and allowed_file(file.filename):
            img_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], img_filename))

    c.execute(
        "UPDATE fighters SET nom=%s, categorie=%s, victoires=%s, defaites=%s, nuls=%s, points=%s, img=%s WHERE id=%s",
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
    c = conn.cursor()
    c.execute("DELETE FROM fighters WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    flash("Combattant supprimé.")
    return redirect("/admin")

# ── ADMIN COMBATS ─────────────────────────────────────────

@app.route("/admin/fight/add", methods=["POST"])
@admin_required
def add_fight():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO fights (fighter1_id, fighter2_id, date, lieu, categorie) VALUES (%s,%s,%s,%s,%s)",
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
    c = conn.cursor()
    c.execute("DELETE FROM fights WHERE id=%s", (id,))
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
    c = conn.cursor()
    c.execute("SELECT * FROM fights WHERE id=%s", (fight_id,))
    fight = fetchone_dict(c)

    if fight:
        perdant_id = fight["fighter2_id"] if gagnant_id == fight["fighter1_id"] else fight["fighter1_id"]

        c.execute("SELECT nom FROM fighters WHERE id=%s", (fight["fighter1_id"],))
        f1 = fetchone_dict(c)
        c.execute("SELECT nom FROM fighters WHERE id=%s", (fight["fighter2_id"],))
        f2 = fetchone_dict(c)

        c.execute(
            "INSERT INTO results (fight_id, gagnant_id, methode, nom1, nom2, date) VALUES (%s,%s,%s,%s,%s,%s)",
            (fight_id, gagnant_id, methode,
             f1["nom"] if f1 else "", f2["nom"] if f2 else "", fight["date"])
        )

        points_map = {
            "KO":                   250,
            "TKO":                  220,
            "Soumission":           220,
            "Décision unanime":     200,
            "Décision majoritaire": 190,
            "Décision partagée":    180,
            "No Contest":           0,
        }
        points_gagnes = points_map.get(methode, 200)

        c.execute("UPDATE fighters SET victoires = victoires + 1, points = points + %s WHERE id=%s", (points_gagnes, gagnant_id))
        c.execute("UPDATE fighters SET defaites = defaites + 1 WHERE id=%s", (perdant_id,))
        c.execute("DELETE FROM fights WHERE id=%s", (fight_id,))
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
    c = conn.cursor()
    c.execute("DELETE FROM results WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    flash("Résultat supprimé.")
    return redirect("/admin")

# ── MAIN ──────────────────────────────────────────────────

init_db()

if __name__ == "__main__":
    app.run(debug=True)
