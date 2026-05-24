"""Работа с базой данных SQLite для «Игротеки вожатого»."""
import sqlite3
from contextlib import contextmanager

DB_PATH = "igroteka.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS Inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                total_quantity INTEGER NOT NULL CHECK(total_quantity >= 0),
                available_quantity INTEGER NOT NULL CHECK(available_quantity >= 0)
            );
            CREATE TABLE IF NOT EXISTS Games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                age_group TEXT NOT NULL,
                inventory_required INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS Game_Inventory (
                game_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                quantity_per_game INTEGER NOT NULL CHECK(quantity_per_game > 0),
                PRIMARY KEY (game_id, inventory_id),
                FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE,
                FOREIGN KEY (inventory_id) REFERENCES Inventory(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS Activity_Log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                counselor_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS Session_Inventory (
                log_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                quantity_used INTEGER NOT NULL CHECK(quantity_used > 0),
                PRIMARY KEY (log_id, inventory_id),
                FOREIGN KEY (log_id) REFERENCES Activity_Log(id) ON DELETE CASCADE,
                FOREIGN KEY (inventory_id) REFERENCES Inventory(id) ON DELETE CASCADE
            );
        """)
        if c.execute("SELECT COUNT(*) FROM Games").fetchone()[0] == 0:
            _seed(conn)


def _seed(conn):
    c = conn.cursor()
    inv = [
        ("Мяч футбольный", 5),
        ("Мяч волейбольный", 3),
        ("Скакалка", 10),
        ("Обруч", 6),
        ("Кегли (набор)", 2),
        ("Повязка на глаза", 8),
        ("Карточки с заданиями", 4),
        ("Маркеры (набор)", 5),
    ]
    for name, qty in inv:
        c.execute(
            "INSERT INTO Inventory(name, total_quantity, available_quantity) VALUES(?,?,?)",
            (name, qty, qty),
        )
    games = [
        ("Вышибалы", "подвижная", "10-14", 1, [("Мяч волейбольный", 1)]),
        ("Море волнуется раз", "подвижная", "6-10", 0, []),
        ("Снежный ком (имена)", "на знакомство", "6-16", 0, []),
        ("Крокодил", "интеллектуальная", "10-16", 1, [("Карточки с заданиями", 1)]),
        ("Эстафета со скакалками", "подвижная", "8-14", 1, [("Скакалка", 4)]),
        ("Жмурки", "подвижная", "6-12", 1, [("Повязка на глаза", 1)]),
        ("Городки/кегли", "подвижная", "8-14", 1, [("Кегли (набор)", 1), ("Мяч футбольный", 1)]),
        ("Что? Где? Когда?", "интеллектуальная", "12-16", 1, [("Маркеры (набор)", 1)]),
        ("Ассоциации", "на знакомство", "10-16", 0, []),
        ("Футбол", "подвижная", "10-16", 1, [("Мяч футбольный", 1)]),
    ]
    for name, typ, age, req, items in games:
        c.execute(
            "INSERT INTO Games(name, type, age_group, inventory_required) VALUES(?,?,?,?)",
            (name, typ, age, req),
        )
        gid = c.lastrowid
        for inv_name, qty in items:
            iid = c.execute("SELECT id FROM Inventory WHERE name=?", (inv_name,)).fetchone()[0]
            c.execute(
                "INSERT INTO Game_Inventory(game_id, inventory_id, quantity_per_game) VALUES(?,?,?)",
                (gid, iid, qty),
            )


# ---------- Games ----------
def list_games(search="", type_filter="", age_filter=""):
    q = "SELECT * FROM Games WHERE 1=1"
    params = []
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    if type_filter:
        q += " AND type=?"
        params.append(type_filter)
    if age_filter:
        q += " AND age_group=?"
        params.append(age_filter)
    q += " ORDER BY name"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def get_game(game_id):
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM Games WHERE id=?", (game_id,)).fetchone()
        return dict(r) if r else None


def add_game(name, typ, age, items):
    """items: список (inventory_id, quantity_per_game)."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO Games(name, type, age_group, inventory_required) VALUES(?,?,?,?)",
            (name, typ, age, 1 if items else 0),
        )
        gid = c.lastrowid
        for iid, qty in items:
            c.execute(
                "INSERT INTO Game_Inventory(game_id, inventory_id, quantity_per_game) VALUES(?,?,?)",
                (gid, iid, qty),
            )
        return gid


def update_game(game_id, name, typ, age, items):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE Games SET name=?, type=?, age_group=?, inventory_required=? WHERE id=?",
            (name, typ, age, 1 if items else 0, game_id),
        )
        c.execute("DELETE FROM Game_Inventory WHERE game_id=?", (game_id,))
        for iid, qty in items:
            c.execute(
                "INSERT INTO Game_Inventory(game_id, inventory_id, quantity_per_game) VALUES(?,?,?)",
                (gid := game_id, iid, qty),
            )


def delete_game(game_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM Games WHERE id=?", (game_id,))


def get_game_inventory(game_id):
    """Возвращает список dict: inventory_id, name, quantity_per_game, available_quantity."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT i.id AS inventory_id, i.name, gi.quantity_per_game, i.available_quantity, i.total_quantity
            FROM Game_Inventory gi JOIN Inventory i ON i.id = gi.inventory_id
            WHERE gi.game_id=?
        """, (game_id,)).fetchall()
        return [dict(r) for r in rows]


def get_distinct(field):
    with get_conn() as conn:
        return [r[0] for r in conn.execute(f"SELECT DISTINCT {field} FROM Games ORDER BY {field}").fetchall()]


# ---------- Inventory ----------
def list_inventory():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM Inventory ORDER BY name").fetchall()]


def add_inventory(name, total):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO Inventory(name, total_quantity, available_quantity) VALUES(?,?,?)",
            (name, total, total),
        )


def update_inventory(inv_id, name, total):
    """При изменении total корректируем available на дельту."""
    with get_conn() as conn:
        cur = conn.execute("SELECT total_quantity, available_quantity FROM Inventory WHERE id=?", (inv_id,)).fetchone()
        delta = total - cur["total_quantity"]
        new_avail = max(0, cur["available_quantity"] + delta)
        if new_avail > total:
            new_avail = total
        conn.execute(
            "UPDATE Inventory SET name=?, total_quantity=?, available_quantity=? WHERE id=?",
            (name, total, new_avail, inv_id),
        )


def delete_inventory(inv_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM Inventory WHERE id=?", (inv_id,))


# ---------- Activity / бронирование ----------
def start_game(game_id, counselor, reservations):
    """reservations: список (inventory_id, quantity). Атомарно резервирует и пишет лог.
    Возвращает (True, log_id) или (False, сообщение об ошибке)."""
    from datetime import datetime
    with get_conn() as conn:
        c = conn.cursor()
        for iid, qty in reservations:
            if qty <= 0:
                return False, "Количество должно быть положительным."
            row = c.execute("SELECT name, available_quantity FROM Inventory WHERE id=?", (iid,)).fetchone()
            if not row:
                return False, "Инвентарь не найден."
            if row["available_quantity"] < qty:
                return False, (
                    f"Инвентарь занят: «{row['name']}» — доступно {row['available_quantity']}, "
                    f"запрошено {qty}. Игра недоступна для выбора."
                )
        for iid, qty in reservations:
            c.execute(
                "UPDATE Inventory SET available_quantity = available_quantity - ? WHERE id=?",
                (qty, iid),
            )
        c.execute(
            "INSERT INTO Activity_Log(game_id, counselor_name, start_time) VALUES(?,?,?)",
            (game_id, counselor, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        log_id = c.lastrowid
        for iid, qty in reservations:
            c.execute(
                "INSERT INTO Session_Inventory(log_id, inventory_id, quantity_used) VALUES(?,?,?)",
                (log_id, iid, qty),
            )
        return True, log_id


def end_game(log_id):
    from datetime import datetime
    with get_conn() as conn:
        c = conn.cursor()
        for r in c.execute("SELECT inventory_id, quantity_used FROM Session_Inventory WHERE log_id=?", (log_id,)).fetchall():
            c.execute(
                "UPDATE Inventory SET available_quantity = MIN(total_quantity, available_quantity + ?) WHERE id=?",
                (r["quantity_used"], r["inventory_id"]),
            )
        c.execute(
            "UPDATE Activity_Log SET end_time=? WHERE id=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), log_id),
        )


def list_active_sessions():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT a.id, a.counselor_name, a.start_time, g.name AS game_name
            FROM Activity_Log a JOIN Games g ON g.id = a.game_id
            WHERE a.end_time IS NULL ORDER BY a.start_time DESC
        """).fetchall()
        return [dict(r) for r in rows]


def list_all_log():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT a.id, a.counselor_name, a.start_time, a.end_time, g.name AS game_name
            FROM Activity_Log a JOIN Games g ON g.id = a.game_id
            ORDER BY a.start_time DESC
        """).fetchall()
        return [dict(r) for r in rows]


def stats_popular_games(limit=10):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT g.name, COUNT(a.id) AS plays
            FROM Games g LEFT JOIN Activity_Log a ON a.game_id = g.id
            GROUP BY g.id ORDER BY plays DESC, g.name LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def stats_counselors():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT counselor_name, COUNT(*) AS plays
            FROM Activity_Log GROUP BY counselor_name ORDER BY plays DESC
        """).fetchall()
        return [dict(r) for r in rows]
