from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "umkm_jus_secret"


# 1. KONEKSI DATABASE
def koneksi_database():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# 2. MEMBUAT DATABASE
def buat_database():
    conn = koneksi_database()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS produk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            kategori TEXT,
            harga INTEGER,
            modal INTEGER
        )
    """)

    jumlah = conn.execute(
        "SELECT COUNT(*) FROM produk"
    ).fetchone()[0]

    if jumlah == 0:
        daftar_produk = [
            ("Jus Jeruk", "Jus", 10000, None),
            ("Jus Belimbing", "Jus", 10000, None),
            ("Jus Kuini", "Jus", 10000, None),
            ("Jus Mangga", "Jus", 10000, None),
            ("Jus Alpukat", "Jus", 10000, None),
            ("Jus Terong Belanda", "Jus", 10000, None),
            ("Jus Buah Naga", "Jus", 10000, None),
            ("Smoothies Mangga", "Smoothies", 15000, None),
            ("Smoothies Strawberry", "Smoothies", 15000, None),
            ("Smoothies Alpukat", "Smoothies", 15000, None)
        ]

        conn.executemany("""
            INSERT INTO produk
            (nama, kategori, harga, modal)
            VALUES (?, ?, ?, ?)
        """, daftar_produk)

    # TABEL TRANSAKSI
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
            total INTEGER
        )
    """)

    # TABEL DETAIL TRANSAKSI
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detail_transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaksi_id INTEGER,
            produk_id INTEGER,
            nama_produk TEXT,
            harga INTEGER,
            modal INTEGER,
            jumlah INTEGER,
            subtotal INTEGER
        )
    """)

    conn.commit()
    conn.close()


# 3. DASHBOARD
@app.route("/")
def home():
    conn = koneksi_database()

    omzet = conn.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM transaksi
    """).fetchone()[0]

    transaksi = conn.execute("""
        SELECT COUNT(*)
        FROM transaksi
    """).fetchone()[0]

    produk_terjual = conn.execute("""
        SELECT COALESCE(SUM(jumlah), 0)
        FROM detail_transaksi
    """).fetchone()[0]

    modal_kosong = conn.execute("""
        SELECT COUNT(*)
        FROM detail_transaksi
        WHERE modal IS NULL
    """).fetchone()[0]

    if modal_kosong > 0:
        laba_kotor = None
    else:
        laba_kotor = conn.execute("""
            SELECT COALESCE(SUM((harga - modal) * jumlah), 0)
            FROM detail_transaksi
        """).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        omzet=omzet,
        transaksi=transaksi,
        produk_terjual=produk_terjual,
        laba_kotor=laba_kotor
    )


# 4. HALAMAN PENJUALAN
@app.route("/penjualan")
def penjualan():
    conn = koneksi_database()

    produk = conn.execute(
        "SELECT * FROM produk"
    ).fetchall()

    conn.close()

    return render_template("penjualan.html", produk=produk)


# 5. PROSES CHECKOUT
@app.route("/checkout", methods=["POST"])
def checkout():
    produk_id = request.form.get("produk_id", type=int)
    jumlah = request.form.get("jumlah", type=int)

    if not produk_id or not jumlah or jumlah < 1:
        flash("Produk atau jumlah pembelian tidak valid.")
        return redirect(url_for("penjualan"))

    conn = koneksi_database()

    produk = conn.execute(
        "SELECT * FROM produk WHERE id = ?",
        (produk_id,)
    ).fetchone()

    if produk is None:
        conn.close()
        flash("Produk tidak ditemukan.")
        return redirect(url_for("penjualan"))

    subtotal = produk["harga"] * jumlah

    cursor = conn.execute("""
        INSERT INTO transaksi (total)
        VALUES (?)
    """, (subtotal,))

    transaksi_id = cursor.lastrowid

    conn.execute("""
        INSERT INTO detail_transaksi
        (transaksi_id, produk_id, nama_produk,
         harga, modal, jumlah, subtotal)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        transaksi_id,
        produk["id"],
        produk["nama"],
        produk["harga"],
        produk["modal"],
        jumlah,
        subtotal
    ))

    conn.commit()
    conn.close()

    flash("Transaksi berhasil disimpan!")

    return redirect(url_for("penjualan"))


# 6. UPDATE MODAL PRODUK
@app.route("/update-modal", methods=["POST"])
def update_modal():
    produk_id = request.form.get("produk_id", type=int)
    modal = request.form.get("modal", type=int)

    if not produk_id or modal is None or modal < 0:
        flash("Modal produk tidak valid.")
        return redirect(url_for("penjualan"))

    conn = koneksi_database()

    conn.execute("""
        UPDATE produk
        SET modal = ?
        WHERE id = ?
    """, (modal, produk_id))

    conn.commit()
    conn.close()

    flash("Modal produk berhasil diperbarui!")

    return redirect(url_for("penjualan"))


# 7. RIWAYAT TRANSAKSI
@app.route("/riwayat")
def riwayat():
    conn = koneksi_database()

    transaksi = conn.execute("""
        SELECT * FROM transaksi
        ORDER BY id DESC
    """).fetchall()

    detail = conn.execute("""
        SELECT * FROM detail_transaksi
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "riwayat.html",
        transaksi=transaksi,
        detail=detail
    )
# 8. MENGHAPUS TRANSAKSI
@app.route("/hapus-transaksi/<int:id>", methods=["POST"])
def hapus_transaksi(id):
    conn = koneksi_database()

    # Hapus detail transaksi terlebih dahulu
    conn.execute("""
        DELETE FROM detail_transaksi
        WHERE transaksi_id = ?
    """, (id,))

    # Hapus data transaksi
    conn.execute("""
        DELETE FROM transaksi
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    flash("Transaksi berhasil dihapus!")

    return redirect(url_for("riwayat"))


# 8. MENJALANKAN WEBSITE
buat_database()
if __name__ == "__main__":
    app.run(debug=True)