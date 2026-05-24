"""Игротека вожатого — главное окно (Tkinter)."""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database as db

GAME_TYPES = ["подвижная", "интеллектуальная", "на знакомство"]


class GameEditor(tk.Toplevel):
    """Модальное окно добавления/редактирования игры."""

    def __init__(self, master, game_id=None, on_save=None):
        super().__init__(master)
        self.game_id = game_id
        self.on_save = on_save
        self.title("Редактирование игры" if game_id else "Новая игра")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        self.var_name = tk.StringVar()
        self.var_type = tk.StringVar()
        self.var_age = tk.StringVar()

        frm = ttk.Frame(self, padding=10)
        frm.grid(sticky="nsew")

        ttk.Label(frm, text="Название:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=self.var_name, width=40).grid(row=0, column=1, columnspan=2, sticky="we")

        ttk.Label(frm, text="Тип:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Combobox(frm, textvariable=self.var_type, values=GAME_TYPES, state="readonly").grid(
            row=1, column=1, columnspan=2, sticky="we")

        ttk.Label(frm, text="Возрастная группа:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=self.var_age).grid(row=2, column=1, columnspan=2, sticky="we")

        ttk.Label(frm, text="Реквизит на игру:").grid(row=3, column=0, sticky="nw", pady=(10, 3))
        self.items_tree = ttk.Treeview(frm, columns=("name", "qty"), show="headings", height=5)
        self.items_tree.heading("name", text="Инвентарь")
        self.items_tree.heading("qty", text="Кол-во")
        self.items_tree.column("name", width=220)
        self.items_tree.column("qty", width=70, anchor="center")
        self.items_tree.grid(row=3, column=1, columnspan=2, sticky="we", pady=(10, 3))

        btns_inv = ttk.Frame(frm)
        btns_inv.grid(row=4, column=1, columnspan=2, sticky="w", pady=3)
        ttk.Button(btns_inv, text="Добавить реквизит", command=self.add_item).pack(side="left", padx=2)
        ttk.Button(btns_inv, text="Удалить выделенный", command=self.remove_item).pack(side="left", padx=2)

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=3, pady=10)
        ttk.Button(btns, text="Сохранить", command=self.save).pack(side="left", padx=5)
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="left", padx=5)

        # хранилище: iid дерева -> (inventory_id, qty)
        self.items = {}

        if game_id:
            g = db.get_game(game_id)
            self.var_name.set(g["name"])
            self.var_type.set(g["type"])
            self.var_age.set(g["age_group"])
            for it in db.get_game_inventory(game_id):
                iid = self.items_tree.insert("", "end", values=(it["name"], it["quantity_per_game"]))
                self.items[iid] = (it["inventory_id"], it["quantity_per_game"])
        else:
            self.var_type.set(GAME_TYPES[0])

    def add_item(self):
        inv_list = db.list_inventory()
        if not inv_list:
            messagebox.showinfo("Склад пуст", "Сначала добавьте инвентарь на вкладке «Склад».", parent=self)
            return
        used_ids = {v[0] for v in self.items.values()}
        choices = [i for i in inv_list if i["id"] not in used_ids]
        if not choices:
            messagebox.showinfo("Готово", "Весь инвентарь уже добавлен.", parent=self)
            return
        PickInventory(self, choices, self._on_item_picked)

    def _on_item_picked(self, inv_id, inv_name, qty):
        iid = self.items_tree.insert("", "end", values=(inv_name, qty))
        self.items[iid] = (inv_id, qty)

    def remove_item(self):
        for iid in self.items_tree.selection():
            self.items_tree.delete(iid)
            self.items.pop(iid, None)

    def save(self):
        name = self.var_name.get().strip()
        typ = self.var_type.get().strip()
        age = self.var_age.get().strip()
        if not name or not typ or not age:
            messagebox.showwarning("Проверка", "Заполните название, тип и возраст.", parent=self)
            return
        items = list(self.items.values())
        if self.game_id:
            db.update_game(self.game_id, name, typ, age, items)
        else:
            db.add_game(name, typ, age, items)
        if self.on_save:
            self.on_save()
        self.destroy()


class PickInventory(tk.Toplevel):
    """Диалог: выбор предмета и количества для игры."""

    def __init__(self, master, choices, callback):
        super().__init__(master)
        self.title("Выбор реквизита")
        self.transient(master)
        self.grab_set()
        self.callback = callback
        self.choices = choices

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Инвентарь:").grid(row=0, column=0, sticky="w")
        self.var_inv = tk.StringVar()
        names = [f"{c['name']} (всего {c['total_quantity']})" for c in choices]
        self.cb = ttk.Combobox(frm, textvariable=self.var_inv, values=names, state="readonly", width=35)
        self.cb.grid(row=0, column=1, pady=3)
        self.cb.current(0)

        ttk.Label(frm, text="Количество на одну игру:").grid(row=1, column=0, sticky="w")
        self.var_qty = tk.IntVar(value=1)
        ttk.Spinbox(frm, from_=1, to=999, textvariable=self.var_qty, width=10).grid(row=1, column=1, sticky="w", pady=3)

        ttk.Button(frm, text="OK", command=self.ok).grid(row=2, column=0, columnspan=2, pady=8)

    def ok(self):
        idx = self.cb.current()
        if idx < 0:
            return
        qty = self.var_qty.get()
        if qty <= 0:
            messagebox.showwarning("Проверка", "Количество должно быть положительным.", parent=self)
            return
        c = self.choices[idx]
        if qty > c["total_quantity"]:
            messagebox.showwarning("Проверка",
                                   f"В лагере всего {c['total_quantity']} шт. этого инвентаря.", parent=self)
            return
        self.callback(c["id"], c["name"], qty)
        self.destroy()


class StartGameDialog(tk.Toplevel):
    """Запуск игры: ввод имени вожатого + проверка/корректировка количества."""

    def __init__(self, master, game, on_started):
        super().__init__(master)
        self.title(f"Начать игру: {game['name']}")
        self.transient(master)
        self.grab_set()
        self.game = game
        self.on_started = on_started

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Имя вожатого:").grid(row=0, column=0, sticky="w", pady=3)
        self.var_name = tk.StringVar()
        ttk.Entry(frm, textvariable=self.var_name, width=30).grid(row=0, column=1, columnspan=2, sticky="we", pady=3)

        self.required = db.get_game_inventory(game["id"])
        self.qty_vars = []  # (inv_id, IntVar, available)

        if self.required:
            ttk.Label(frm, text="Реквизит (можно скорректировать количество):").grid(
                row=1, column=0, columnspan=3, sticky="w", pady=(10, 3))
            for i, it in enumerate(self.required, start=2):
                ttk.Label(frm, text=f"• {it['name']}").grid(row=i, column=0, sticky="w")
                ttk.Label(frm, text=f"доступно: {it['available_quantity']}").grid(row=i, column=1, sticky="w", padx=8)
                v = tk.IntVar(value=it["quantity_per_game"])
                ttk.Spinbox(frm, from_=1, to=max(1, it["available_quantity"]),
                            textvariable=v, width=6).grid(row=i, column=2, sticky="w")
                self.qty_vars.append((it["inventory_id"], v, it["available_quantity"], it["name"]))
        else:
            ttk.Label(frm, text="Реквизит не требуется.").grid(row=1, column=0, columnspan=3, pady=8)

        ttk.Button(frm, text="Начать", command=self.start).grid(row=99, column=0, columnspan=3, pady=10)

    def start(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showwarning("Проверка", "Введите имя вожатого.", parent=self)
            return
        reservations = []
        for iid, var, avail, inv_name in self.qty_vars:
            q = var.get()
            if q <= 0:
                messagebox.showwarning("Проверка", f"«{inv_name}»: количество должно быть > 0.", parent=self)
                return
            if q > avail:
                messagebox.showerror("Инвентарь занят",
                                     f"«{inv_name}»: доступно только {avail}.", parent=self)
                return
            reservations.append((iid, q))
        ok, result = db.start_game(self.game["id"], name, reservations)
        if not ok:
            messagebox.showerror("Невозможно начать игру", result, parent=self)
            return
        messagebox.showinfo("Готово", "Игра начата. Реквизит зарезервирован.", parent=self)
        self.on_started()
        self.destroy()


class InventoryEditor(tk.Toplevel):
    def __init__(self, master, inv_id=None, on_save=None):
        super().__init__(master)
        self.inv_id = inv_id
        self.on_save = on_save
        self.title("Редактирование инвентаря" if inv_id else "Новый инвентарь")
        self.transient(master)
        self.grab_set()

        self.var_name = tk.StringVar()
        self.var_total = tk.IntVar(value=1)

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Название:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=self.var_name, width=30).grid(row=0, column=1, pady=3)
        ttk.Label(frm, text="Общее количество:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Spinbox(frm, from_=0, to=9999, textvariable=self.var_total, width=10).grid(row=1, column=1, sticky="w", pady=3)

        ttk.Button(frm, text="Сохранить", command=self.save).grid(row=2, column=0, columnspan=2, pady=8)

        if inv_id:
            for inv in db.list_inventory():
                if inv["id"] == inv_id:
                    self.var_name.set(inv["name"])
                    self.var_total.set(inv["total_quantity"])
                    break

    def save(self):
        name = self.var_name.get().strip()
        total = self.var_total.get()
        if not name:
            messagebox.showwarning("Проверка", "Введите название.", parent=self)
            return
        if total < 0:
            messagebox.showwarning("Проверка", "Количество не может быть отрицательным.", parent=self)
            return
        try:
            if self.inv_id:
                db.update_inventory(self.inv_id, name, total)
            else:
                db.add_inventory(name, total)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)
            return
        if self.on_save:
            self.on_save()
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Игротека вожатого")
        self.geometry("1000x600")
        db.init_db()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.tab_games = ttk.Frame(nb)
        self.tab_inv = ttk.Frame(nb)
        self.tab_active = ttk.Frame(nb)
        self.tab_stats = ttk.Frame(nb)
        self.tab_help = ttk.Frame(nb)
        nb.add(self.tab_games, text="Игры")
        nb.add(self.tab_inv, text="Склад")
        nb.add(self.tab_active, text="Активные игры")
        nb.add(self.tab_stats, text="Статистика")
        nb.add(self.tab_help, text="Справка")

        self._build_games_tab()
        self._build_inv_tab()
        self._build_active_tab()
        self._build_stats_tab()
        self._build_help_tab()

        nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())
        self.refresh_all()

    # ---------- Игры ----------
    def _build_games_tab(self):
        top = ttk.Frame(self.tab_games, padding=5)
        top.pack(fill="x")

        ttk.Label(top, text="Поиск:").pack(side="left")
        self.var_search = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.var_search, width=25)
        ent.pack(side="left", padx=4)
        ent.bind("<KeyRelease>", lambda e: self.refresh_games())

        ttk.Label(top, text="Тип:").pack(side="left", padx=(10, 0))
        self.var_ftype = tk.StringVar()
        self.cb_type = ttk.Combobox(top, textvariable=self.var_ftype, state="readonly", width=18)
        self.cb_type.pack(side="left", padx=4)
        self.cb_type.bind("<<ComboboxSelected>>", lambda e: self.refresh_games())

        ttk.Label(top, text="Возраст:").pack(side="left", padx=(10, 0))
        self.var_fage = tk.StringVar()
        self.cb_age = ttk.Combobox(top, textvariable=self.var_fage, state="readonly", width=12)
        self.cb_age.pack(side="left", padx=4)
        self.cb_age.bind("<<ComboboxSelected>>", lambda e: self.refresh_games())

        ttk.Button(top, text="Сброс", command=self.reset_filters).pack(side="left", padx=4)

        cols = ("id", "name", "type", "age", "inv")
        self.tree_games = ttk.Treeview(self.tab_games, columns=cols, show="headings")
        for c, t, w in [("id", "ID", 40), ("name", "Название", 280),
                        ("type", "Тип", 140), ("age", "Возраст", 100),
                        ("inv", "Реквизит", 380)]:
            self.tree_games.heading(c, text=t)
            self.tree_games.column(c, width=w, anchor="w")
        self.tree_games.pack(fill="both", expand=True, padx=5, pady=5)

        btns = ttk.Frame(self.tab_games)
        btns.pack(fill="x", padx=5, pady=5)
        ttk.Button(btns, text="Начать игру", command=self.start_selected_game).pack(side="left", padx=2)
        ttk.Button(btns, text="Добавить", command=lambda: GameEditor(self, on_save=self.refresh_all)).pack(side="left", padx=2)
        ttk.Button(btns, text="Редактировать", command=self.edit_selected_game).pack(side="left", padx=2)
        ttk.Button(btns, text="Удалить", command=self.delete_selected_game).pack(side="left", padx=2)

    def reset_filters(self):
        self.var_search.set("")
        self.var_ftype.set("")
        self.var_fage.set("")
        self.refresh_games()

    def refresh_games(self):
        for i in self.tree_games.get_children():
            self.tree_games.delete(i)
        games = db.list_games(self.var_search.get(), self.var_ftype.get(), self.var_fage.get())
        for g in games:
            items = db.get_game_inventory(g["id"])
            inv_str = ", ".join(f"{it['name']}×{it['quantity_per_game']}" for it in items) if items else "—"
            self.tree_games.insert("", "end", values=(g["id"], g["name"], g["type"], g["age_group"], inv_str))
        types = [""] + db.get_distinct("type")
        ages = [""] + db.get_distinct("age_group")
        self.cb_type["values"] = types
        self.cb_age["values"] = ages

    def _selected_game_id(self):
        sel = self.tree_games.selection()
        if not sel:
            messagebox.showinfo("Выбор", "Сначала выделите игру в таблице.")
            return None
        return int(self.tree_games.item(sel[0], "values")[0])

    def edit_selected_game(self):
        gid = self._selected_game_id()
        if gid:
            GameEditor(self, game_id=gid, on_save=self.refresh_all)

    def delete_selected_game(self):
        gid = self._selected_game_id()
        if not gid:
            return
        if messagebox.askyesno("Удалить", "Удалить выбранную игру?"):
            db.delete_game(gid)
            self.refresh_all()

    def start_selected_game(self):
        gid = self._selected_game_id()
        if not gid:
            return
        g = db.get_game(gid)
        StartGameDialog(self, g, on_started=self.refresh_all)

    # ---------- Склад ----------
    def _build_inv_tab(self):
        cols = ("id", "name", "total", "avail")
        self.tree_inv = ttk.Treeview(self.tab_inv, columns=cols, show="headings")
        for c, t, w in [("id", "ID", 40), ("name", "Название", 320),
                        ("total", "Всего", 80), ("avail", "Доступно", 80)]:
            self.tree_inv.heading(c, text=t)
            self.tree_inv.column(c, width=w, anchor="w")
        self.tree_inv.pack(fill="both", expand=True, padx=5, pady=5)

        btns = ttk.Frame(self.tab_inv)
        btns.pack(fill="x", padx=5, pady=5)
        ttk.Button(btns, text="Добавить", command=lambda: InventoryEditor(self, on_save=self.refresh_all)).pack(side="left", padx=2)
        ttk.Button(btns, text="Редактировать", command=self.edit_selected_inv).pack(side="left", padx=2)
        ttk.Button(btns, text="Удалить", command=self.delete_selected_inv).pack(side="left", padx=2)

    def _selected_inv_id(self):
        sel = self.tree_inv.selection()
        if not sel:
            messagebox.showinfo("Выбор", "Сначала выделите предмет.")
            return None
        return int(self.tree_inv.item(sel[0], "values")[0])

    def edit_selected_inv(self):
        iid = self._selected_inv_id()
        if iid:
            InventoryEditor(self, inv_id=iid, on_save=self.refresh_all)

    def delete_selected_inv(self):
        iid = self._selected_inv_id()
        if not iid:
            return
        if messagebox.askyesno("Удалить", "Удалить выбранный инвентарь? Он будет убран из всех игр."):
            db.delete_inventory(iid)
            self.refresh_all()

    def refresh_inv(self):
        for i in self.tree_inv.get_children():
            self.tree_inv.delete(i)
        for inv in db.list_inventory():
            self.tree_inv.insert("", "end", values=(inv["id"], inv["name"], inv["total_quantity"], inv["available_quantity"]))

    # ---------- Активные ----------
    def _build_active_tab(self):
        cols = ("id", "game", "counselor", "start")
        self.tree_active = ttk.Treeview(self.tab_active, columns=cols, show="headings")
        for c, t, w in [("id", "№", 50), ("game", "Игра", 300),
                        ("counselor", "Вожатый", 200), ("start", "Начало", 180)]:
            self.tree_active.heading(c, text=t)
            self.tree_active.column(c, width=w, anchor="w")
        self.tree_active.pack(fill="both", expand=True, padx=5, pady=5)
        btns = ttk.Frame(self.tab_active)
        btns.pack(fill="x", padx=5, pady=5)
        ttk.Button(btns, text="Завершить выбранную игру (вернуть инвентарь)", command=self.end_selected).pack(side="left", padx=2)
        ttk.Button(btns, text="Обновить", command=self.refresh_active).pack(side="left", padx=2)

    def end_selected(self):
        sel = self.tree_active.selection()
        if not sel:
            messagebox.showinfo("Выбор", "Выделите активную игру.")
            return
        log_id = int(self.tree_active.item(sel[0], "values")[0])
        db.end_game(log_id)
        self.refresh_all()

    def refresh_active(self):
        for i in self.tree_active.get_children():
            self.tree_active.delete(i)
        for r in db.list_active_sessions():
            self.tree_active.insert("", "end", values=(r["id"], r["game_name"], r["counselor_name"], r["start_time"]))

    # ---------- Статистика ----------
    def _build_stats_tab(self):
        outer = ttk.Frame(self.tab_stats, padding=5)
        outer.pack(fill="both", expand=True)

        left = ttk.LabelFrame(outer, text="Самые популярные игры", padding=5)
        left.pack(side="left", fill="both", expand=True, padx=4)
        self.tree_pop = ttk.Treeview(left, columns=("name", "plays"), show="headings")
        self.tree_pop.heading("name", text="Игра"); self.tree_pop.heading("plays", text="Запусков")
        self.tree_pop.column("name", width=240); self.tree_pop.column("plays", width=80, anchor="center")
        self.tree_pop.pack(fill="both", expand=True)

        mid = ttk.LabelFrame(outer, text="Вожатые", padding=5)
        mid.pack(side="left", fill="both", expand=True, padx=4)
        self.tree_couns = ttk.Treeview(mid, columns=("name", "plays"), show="headings")
        self.tree_couns.heading("name", text="Имя"); self.tree_couns.heading("plays", text="Игр проведено")
        self.tree_couns.column("name", width=180); self.tree_couns.column("plays", width=100, anchor="center")
        self.tree_couns.pack(fill="both", expand=True)

        right = ttk.LabelFrame(outer, text="Журнал (кто во что играл)", padding=5)
        right.pack(side="left", fill="both", expand=True, padx=4)
        self.tree_log = ttk.Treeview(right, columns=("game", "couns", "start", "end"), show="headings")
        for c, t, w in [("game", "Игра", 160), ("couns", "Вожатый", 120),
                        ("start", "Начало", 130), ("end", "Конец", 130)]:
            self.tree_log.heading(c, text=t); self.tree_log.column(c, width=w, anchor="w")
        self.tree_log.pack(fill="both", expand=True)

    def refresh_stats(self):
        for i in self.tree_pop.get_children(): self.tree_pop.delete(i)
        for r in db.stats_popular_games():
            self.tree_pop.insert("", "end", values=(r["name"], r["plays"]))
        for i in self.tree_couns.get_children(): self.tree_couns.delete(i)
        for r in db.stats_counselors():
            self.tree_couns.insert("", "end", values=(r["counselor_name"], r["plays"]))
        for i in self.tree_log.get_children(): self.tree_log.delete(i)
        for r in db.list_all_log():
            self.tree_log.insert("", "end", values=(r["game_name"], r["counselor_name"],
                                                    r["start_time"], r["end_time"] or "идёт"))

    # ---------- Справка ----------
    def _build_help_tab(self):
        txt = tk.Text(self.tab_help, wrap="word", padx=10, pady=10)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0",
            "ИГРОТЕКА ВОЖАТОГО — краткая инструкция\n\n"
            "1. Вкладка «Игры» — каталог. Здесь можно искать по названию, фильтровать по типу и возрасту, "
            "добавлять, редактировать и удалять игры. Кнопка «Начать игру» открывает форму запуска: "
            "введите имя вожатого, при необходимости скорректируйте количество реквизита, "
            "и программа автоматически зарезервирует инвентарь.\n\n"
            "2. Если требуемого инвентаря не хватает — программа предупредит «Инвентарь занят, "
            "данная игра недоступна для выбора» и не позволит начать игру.\n\n"
            "3. Вкладка «Склад» — управление реквизитом. Можно добавлять новые предметы, изменять общее "
            "количество (если докупили или что-то сломалось) и удалять. При изменении «всего» доступное "
            "количество корректируется автоматически.\n\n"
            "4. Вкладка «Активные игры» — список начатых, но не завершённых игр. Нажмите «Завершить», "
            "и инвентарь вернётся на склад.\n\n"
            "5. Вкладка «Статистика» — самые популярные игры, статистика по вожатым и полный журнал.\n\n"
            "Важно: пока игра не завершена — её реквизит занят. Не забывайте «закрывать» игры!\n"
        )
        txt.configure(state="disabled")

    # ---------- общее ----------
    def refresh_all(self):
        self.refresh_games()
        self.refresh_inv()
        self.refresh_active()
        self.refresh_stats()


if __name__ == "__main__":
    App().mainloop()
