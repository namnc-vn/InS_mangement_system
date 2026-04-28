import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry # <--- THƯ VIỆN LỊCH
from service import Service
from history import (CommandHistory, AddInventoryCommand, UpdateInventoryQtyCommand,
                      AddProductCommand, AddCategoryCommand, AddWarehouseCommand, 
                      AddStoreCommand, TransferInventoryCommand)
from datetime import datetime, date as date_type
import db_connect

ctk.set_appearance_mode("light")
BG_APP = "#f4f7fe"
BG_CARD = "#ffffff"
TEXT_MAIN = "#111827"
TEXT_SUB = "#6b7280"
PRIMARY_COLOR = "#3b82f6"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Inventory and Store management")
        self.geometry("1250x800")
        self.configure(fg_color=BG_APP)

        self.service = Service()
        self.history = CommandHistory()
        try:
            self.conn = db_connect.get_connection()
            self.cursor = self.conn.cursor()
            self.service.load_data(self.cursor)
        except Exception as e:
            messagebox.showwarning("Lỗi Database", f"Chạy offline mode. Lỗi DB: {e}")

        self.active_tab = "Category" 
        self.current_filter = "ALL"
        self.filter_category_id = None
        self.filter_product_id = None
        self.filter_warehouse_id = None
        self.filter_store_id = None
        # Lọc theo khoảng — Quantity (BST) & Exp Date
        self.range_filter = {"qty_min": None, "qty_max": None,
                             "exp_from": None, "exp_to": None}

        self.style_treeview()
        self.build_top_header()
        self.build_kpi_cards()
        self.build_tabs()
        self.build_main_content()
        # Phím tắt Undo / Redo
        self.bind("<Control-z>", lambda e: self.do_undo())
        self.bind("<Control-y>", lambda e: self.do_redo())

    def style_treeview(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=BG_CARD, foreground=TEXT_MAIN, rowheight=40, 
                        fieldbackground=BG_CARD, borderwidth=0, font=("Inter", 11))
        style.configure("Treeview.Heading", background=BG_CARD, foreground=TEXT_SUB, 
                        font=("Inter", 10, "bold"), borderwidth=0)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.map("Treeview", background=[("selected", "#e0e7ff")], foreground=[("selected", PRIMARY_COLOR)])

    # ==========================================
    # HEADER & THÊM MỚI (TÍCH HỢP TRIE & CALENDAR)
    # ==========================================
    def build_top_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.header_frame.pack(fill="x", padx=30, pady=(20, 10))

        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="Inventory and Store Management", font=("Inter", 24, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="App quản lý kho hàng và cửa hàng", font=("Inter", 13), text_color=TEXT_SUB).pack(anchor="w")

        ctk.CTkButton(self.header_frame, text="⚙️ Cài đặt", fg_color="#f3f4f6", text_color=TEXT_MAIN,
                      hover_color="#e5e7eb", font=("Inter", 13, "bold"), height=40,
                      command=self.open_settings_dialog).pack(side="right", padx=6)

        self.btn_redo = ctk.CTkButton(self.header_frame, text="↪ Redo", fg_color="#f3f4f6",
                                      text_color="#9ca3af", hover_color="#e5e7eb",
                                      font=("Inter", 12, "bold"), height=40, width=90,
                                      state="disabled", command=self.do_redo)
        self.btn_redo.pack(side="right", padx=3)

        self.btn_undo = ctk.CTkButton(self.header_frame, text="↩ Undo", fg_color="#f3f4f6",
                                      text_color="#9ca3af", hover_color="#e5e7eb",
                                      font=("Inter", 12, "bold"), height=40, width=90,
                                      state="disabled", command=self.do_undo)
        self.btn_undo.pack(side="right", padx=3)

        ctk.CTkButton(self.header_frame, text="➕ New Inventory", fg_color=PRIMARY_COLOR, hover_color="#2563eb",
                      font=("Inter", 13, "bold"), height=40, command=self.open_add_inventory_dialog).pack(side="right", padx=6)

    def open_add_inventory_dialog(self):
        """Hộp thoại thêm tồn kho — Autocomplete thực sự với Entry + Listbox nổi"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Inventory")
        dialog.geometry("520x640")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        def make_autocomplete(parent, label_text, get_suggestions_fn):
            """Tạo widget Entry + Listbox gợi ý nổi bên dưới"""
            ctk.CTkLabel(parent, text=label_text,
                         font=("Inter", 12, "bold")).pack(pady=(14, 2), padx=20, anchor="w")

            var = ctk.StringVar()
            entry = ctk.CTkEntry(parent, width=470, height=38, textvariable=var,
                                 font=("Inter", 12))
            entry.pack(padx=20)

            # --- Listbox nổi (floating popup) ---
            popup = tk.Frame(dialog, bg="white", relief="solid", bd=1)
            lb = tk.Listbox(popup, height=6, font=("Inter", 11),
                            selectbackground="#e0e7ff", selectforeground="#3b82f6",
                            bg="white", fg="#111827", bd=0,
                            highlightthickness=0, activestyle="none",
                            cursor="hand2")
            lb.pack(fill="both", expand=True)
            popup_visible = [False]

            def show_popup():
                entry.update_idletasks()
                ex = entry.winfo_rootx() - dialog.winfo_rootx()
                ey = entry.winfo_rooty() - dialog.winfo_rooty() + entry.winfo_height()
                popup.place(x=ex, y=ey, width=entry.winfo_width())
                popup.lift()
                popup_visible[0] = True

            def hide_popup():
                popup.place_forget()
                popup_visible[0] = False

            def on_key_release(event):
                # Bỏ qua phím điều hướng
                if event.keysym in ("Down", "Up", "Return", "Escape"):
                    return
                val = var.get()
                suggestions = get_suggestions_fn(val)[:10] if val else []
                lb.delete(0, "end")
                if suggestions:
                    for s in suggestions:
                        lb.insert("end", s)
                    show_popup()
                else:
                    hide_popup()

            def on_select(event):
                if lb.curselection():
                    var.set(lb.get(lb.curselection()[0]))
                hide_popup()
                entry.focus_set()

            def on_focus_out(event):
                # Delay nhỏ để kịp nhận click vào listbox
                dialog.after(180, hide_popup)

            def navigate(event):
                """Dùng phím mũi tên để di chuyển trong listbox"""
                if not popup_visible[0]:
                    return
                size = lb.size()
                if size == 0:
                    return
                cur = lb.curselection()
                if event.keysym == "Down":
                    idx = (cur[0] + 1) if cur else 0
                    idx = min(idx, size - 1)
                elif event.keysym == "Up":
                    idx = (cur[0] - 1) if cur else size - 1
                    idx = max(idx, 0)
                else:
                    return
                lb.selection_clear(0, "end")
                lb.selection_set(idx)
                lb.see(idx)

            def on_enter(event):
                if popup_visible[0] and lb.curselection():
                    var.set(lb.get(lb.curselection()[0]))
                    hide_popup()

            entry.bind("<KeyRelease>", on_key_release)
            entry.bind("<FocusOut>", on_focus_out)
            entry.bind("<Down>", navigate)
            entry.bind("<Up>", navigate)
            entry.bind("<Return>", on_enter)
            entry.bind("<Escape>", lambda e: hide_popup())
            lb.bind("<ButtonRelease-1>", on_select)

            return var

        # 1. Product ID — autocomplete Trie theo ID
        prod_var = make_autocomplete(
            dialog,
            "Product ID (nhập để gợi ý):",
            self.service.product_id_trie.get_suggestions
        )

        # 2. Batch ID — autocomplete Trie theo Batch
        batch_var = make_autocomplete(
            dialog,
            "Batch ID (nhập để gợi ý):",
            self.service.batch_id_trie.get_suggestions
        )

        # 3. Quantity
        ctk.CTkLabel(dialog, text="Quantity:",
                     font=("Inter", 12, "bold")).pack(pady=(14, 2), padx=20, anchor="w")
        qty_ent = ctk.CTkEntry(dialog, width=470, height=38, font=("Inter", 12))
        qty_ent.pack(padx=20)

        # 4 & 5. Date Pickers
        date_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        date_frame.pack(fill="x", padx=20, pady=12)
        ctk.CTkLabel(date_frame, text="Mfg Date:",
                     font=("Inter", 12, "bold")).pack(side="left", padx=(0, 8))
        mfg_date = DateEntry(date_frame, width=12, background=PRIMARY_COLOR,
                             foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
        mfg_date.pack(side="left")
        ctk.CTkLabel(date_frame, text="Exp Date:",
                     font=("Inter", 12, "bold")).pack(side="left", padx=(30, 8))
        exp_date = DateEntry(date_frame, width=12, background=PRIMARY_COLOR,
                             foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
        exp_date.pack(side="left")

        # 6. Warehouse
        ctk.CTkLabel(dialog, text="Warehouse:",
                     font=("Inter", 12, "bold")).pack(pady=(4, 2), padx=20, anchor="w")
        wh_values = (list(self.service.warehouses_map.keys())
                     or list(set(inv.warehouse_id for inv in self.service.inventory_map.values() if inv.warehouse_id))
                     or ["WH-A", "WH-B"])
        wh_cb = ctk.CTkComboBox(dialog, width=470, values=wh_values, font=("Inter", 12))
        wh_cb.pack(padx=20)
        if wh_values:
            wh_cb.set(wh_values[0])

        def save_inventory():
            p_id = prod_var.get().strip()
            if p_id not in self.service.products_map:
                ask = messagebox.askyesno(
                    "Product Not Found",
                    f"Sản phẩm '{p_id}' chưa có trong hệ thống!\n"
                    "Bạn có muốn tạo mới sản phẩm này không?"
                )
                if ask:
                    self.open_add_product_dialog(p_id)
                return
            try:
                b_id  = batch_var.get().strip()
                mfg   = mfg_date.get_date().strftime("%Y-%m-%d")
                exp   = exp_date.get_date().strftime("%Y-%m-%d")
                wh    = wh_cb.get()
                qty   = int(qty_ent.get())
                # Kiểm tra trước để biết là Update hay Insert (phục vụ Undo)
                existing = self.service.check_item_exist(p_id, b_id, mfg, exp, wh)
                old_qty  = existing.quantity if existing else None
                old_id   = existing.id if existing else None

                self.service.add_inventory_item(p_id, qty, b_id, mfg, exp, wh, self.cursor, self.conn)

                # Tạo và đẩy Command vào history
                if old_qty is not None:
                    cmd = UpdateInventoryQtyCommand(old_id, old_qty, qty)
                else:
                    comp_key = (p_id, b_id, mfg, exp, wh)
                    new_item = self.service.inventory_composite_map.get(comp_key)
                    cmd = AddInventoryCommand(new_item.id, p_id, b_id, mfg, exp, qty, wh)
                self.history.push(cmd)
                self._update_undo_redo_buttons()

                self.build_kpi_cards()
                self.refresh_table()
                dialog.destroy()
                messagebox.showinfo("Success", "Thêm tồn kho thành công!")
            except Exception as e:
                messagebox.showerror("Error", f"Lỗi nhập liệu/CSDL: {e}")

        ctk.CTkButton(dialog, text="💾 Save Inventory", fg_color=PRIMARY_COLOR,
                      hover_color="#2563eb", font=("Inter", 13, "bold"),
                      height=42, width=470, command=save_inventory).pack(pady=18, padx=20)

    def open_add_product_dialog(self, prefill_id):
        p_dialog = ctk.CTkToplevel(self)
        p_dialog.title("Add New Product")
        p_dialog.geometry("450x450")
        p_dialog.attributes("-topmost", True)

        ctk.CTkLabel(p_dialog, text="Product ID:", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        id_ent = ctk.CTkEntry(p_dialog, width=400)
        id_ent.insert(0, prefill_id)
        id_ent.pack(padx=20)

        ctk.CTkLabel(p_dialog, text="Product Name:", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        name_ent = ctk.CTkEntry(p_dialog, width=400)
        name_ent.pack(padx=20)

        # Category Dropdown: Format "ID - Tên", khi lấy sẽ split lấy ID
        ctk.CTkLabel(p_dialog, text="Category Selection:", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        cat_list = [f"{c.id} - {c.name}" for c in self.service.categories_map.values()]
        cat_cb = ctk.CTkComboBox(p_dialog, width=400, values=cat_list)
        cat_cb.pack(padx=20)

        ctk.CTkLabel(p_dialog, text="Price:", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        price_ent = ctk.CTkEntry(p_dialog, width=400)
        price_ent.pack(padx=20)

        def save_product():
            try:
                p_id   = id_ent.get().strip()
                p_name = name_ent.get().strip()
                cat_id = cat_cb.get().split(" - ")[0]
                price  = price_ent.get().strip()
                status = "Active"
                success = self.service.add_product(p_id, p_name, cat_id, price, status, self.cursor, self.conn)
                if success:
                    self.history.push(AddProductCommand(p_id, p_name, cat_id, price, status))
                    self._update_undo_redo_buttons()
                    messagebox.showinfo("Success", "Sản phẩm đã tạo thành công! Bạn có thể lưu Inventory.")
                    p_dialog.destroy()
                else:
                    messagebox.showerror("Error", "ID Sản phẩm đã tồn tại!")
            except Exception as e:
                messagebox.showerror("Error", f"Lỗi CSDL: {e}")

        ctk.CTkButton(p_dialog, text="Save Product", fg_color="#10b981", hover_color="#059669", command=save_product).pack(pady=25)

    def open_settings_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Cài đặt Cảnh báo")
        dialog.geometry("400x300")
        dialog.attributes("-topmost", True)
        
        ctk.CTkLabel(dialog, text="Ngưỡng Số lượng thấp (Low Stock):", font=("Inter", 12)).pack(pady=(20, 5), padx=20, anchor="w")
        low_entry = ctk.CTkEntry(dialog, width=360)
        low_entry.insert(0, str(self.service.settings["low_stock_threshold"]))
        low_entry.pack(padx=20)
        
        ctk.CTkLabel(dialog, text="Ngưỡng Hết hạn (Ngày):", font=("Inter", 12)).pack(pady=(20, 5), padx=20, anchor="w")
        exp_entry = ctk.CTkEntry(dialog, width=360)
        exp_entry.insert(0, str(self.service.settings["expiring_days_threshold"]))
        exp_entry.pack(padx=20)
        
        def save():
            self.service.settings["low_stock_threshold"] = int(low_entry.get())
            self.service.settings["expiring_days_threshold"] = int(exp_entry.get())
            self.build_kpi_cards()
            self.refresh_table()
            dialog.destroy()
                
        ctk.CTkButton(dialog, text="Lưu cấu hình", fg_color=PRIMARY_COLOR, command=save).pack(pady=30)

    # ==========================================
    # CÁC PHẦN CÒN LẠI (GIỮ NGUYÊN)
    # ==========================================
    def build_kpi_cards(self):
        if hasattr(self, 'kpi_container'): self.kpi_container.destroy()

        self.kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_container.pack(fill="x", padx=30, pady=(0, 20), after=self.header_frame)
        self.kpi_container.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="col")

        stats = self.service.get_kpi_stats()
        normal_cards = [
            {"title": "Total Products", "key": "Total Products", "icon": "📦", "bg_icon": "#e0e7ff", "icon_color": "#4f46e5"},
            {"title": "Warehouses", "key": "Warehouses", "icon": "🏢", "bg_icon": "#dcfce7", "icon_color": "#16a34a"},
            {"title": "Inventory Value", "key": "Inventory Value", "icon": "📋", "bg_icon": "#e0e7ff", "icon_color": "#4f46e5"}
        ]

        for i, cfg in enumerate(normal_cards):
            card = ctk.CTkFrame(self.kpi_container, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color="#e5e7eb")
            card.grid(row=0, column=i, padx=8, sticky="nsew")

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", padx=20, pady=20)
            ctk.CTkLabel(info_frame, text=cfg["title"], font=("Inter", 13), text_color=TEXT_SUB).pack(anchor="w")
            ctk.CTkLabel(info_frame, text=stats[cfg["key"]]["value"], font=("Inter", 26, "bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(5,0))
            ctk.CTkLabel(info_frame, text=stats[cfg["key"]]["trend"], font=("Inter", 12), text_color="#10b981").pack(anchor="w")

            icon_box = ctk.CTkFrame(card, fg_color=cfg["bg_icon"], width=45, height=45, corner_radius=10)
            icon_box.pack(side="right", padx=20)
            icon_box.pack_propagate(False)
            ctk.CTkLabel(icon_box, text=cfg["icon"], font=("Inter", 20), text_color=cfg["icon_color"]).place(relx=0.5, rely=0.5, anchor="center")

        alert_card = ctk.CTkFrame(self.kpi_container, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color="#e5e7eb")
        alert_card.grid(row=0, column=3, padx=8, sticky="nsew")
        
        top_alert = ctk.CTkFrame(alert_card, fg_color="transparent")
        top_alert.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(top_alert, text="⚠️ Low Stock:", font=("Inter", 13, "bold"), text_color="#ea580c").pack(side="left")
        ctk.CTkLabel(top_alert, text=f"{stats['Low Stock Count']} items", font=("Inter", 14, "bold"), text_color=TEXT_MAIN).pack(side="right")
        
        ctk.CTkFrame(alert_card, fg_color="#e5e7eb", height=1).pack(fill="x", padx=15)
        
        bot_alert = ctk.CTkFrame(alert_card, fg_color="transparent")
        bot_alert.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkLabel(bot_alert, text="⏳ Expiring Soon:", font=("Inter", 13, "bold"), text_color="#ef4444").pack(side="left")
        ctk.CTkLabel(bot_alert, text=f"{stats['Expiring Count']} items", font=("Inter", 14, "bold"), text_color=TEXT_MAIN).pack(side="right")

    def build_tabs(self):
        tab_frame = ctk.CTkFrame(self, fg_color="transparent", height=45)
        tab_frame.pack(fill="x", padx=38, pady=0)
        self.tab_btns = {}
        tabs = [("🏷️ Category", "Category"), ("📦 Product", "Product"), ("📋 Inventory", "Inventory"), ("🏢 Warehouse", "Warehouse"), ("🏪 Store", "Store")]
        for text, name in tabs:
            btn = ctk.CTkButton(tab_frame, text=text, font=("Inter", 14, "bold"), fg_color="transparent",
                text_color=PRIMARY_COLOR if name == self.active_tab else TEXT_SUB,
                hover_color="#e5e7eb", corner_radius=0, command=lambda n=name: self.switch_tab(n, clear_filter=True))
            btn.pack(side="left", padx=10)
            self.tab_btns[name] = btn
        ctk.CTkFrame(self, fg_color="#e5e7eb", height=1).pack(fill="x", padx=30, pady=(5, 10))

    def switch_tab(self, tab_name, clear_filter=True):
        self.active_tab = tab_name
        for name, btn in self.tab_btns.items():
            btn.configure(text_color=PRIMARY_COLOR if name == self.active_tab else TEXT_SUB)
        self.current_filter = "ALL"
        if clear_filter:
            self.filter_category_id = None
            self.filter_product_id = None
            self.filter_warehouse_id = None
            self.filter_store_id = None
            self.range_filter = {"qty_min": None, "qty_max": None,
                                 "exp_from": None, "exp_to": None}
        self.build_main_content()

    def build_main_content(self):
        if hasattr(self, 'content_area'): self.content_area.destroy()
        self.content_area = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color="#e5e7eb")
        self.content_area.pack(fill="both", expand=True, padx=30, pady=(10, 20))

        toolbar = ctk.CTkFrame(self.content_area, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=20)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(toolbar, textvariable=self.search_var, placeholder_text=f"🔍 KMP Search...", 
                                         width=300, height=38, corner_radius=6)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_table())

        active_filter = self.filter_category_id or self.filter_product_id or self.filter_warehouse_id or self.filter_store_id
        if active_filter:
            msg = f"Đang lọc: {active_filter}"
            ctk.CTkLabel(toolbar, text=msg, text_color="#f97316", font=("Inter", 12, "bold")).pack(side="left", padx=10)
            ctk.CTkButton(toolbar, text="❌ Bỏ lọc", fg_color="#fee2e2", text_color="#b91c1c", hover_color="#fca5a5",
                          width=60, height=35, command=self.clear_drilldown_filters).pack(side="left")

        if self.active_tab == "Inventory":
            filter_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
            filter_frame.pack(side="right")
            self.btn_all = ctk.CTkButton(filter_frame, text="All Items", fg_color=PRIMARY_COLOR, width=80, height=35, command=lambda: self.set_filter("ALL"))
            self.btn_all.pack(side="left", padx=5)
            self.btn_low = ctk.CTkButton(filter_frame, text="⚠️ Low Stock", fg_color="#ffffff", text_color=TEXT_MAIN, border_width=1, width=90, height=35, hover_color="#f3f4f6", command=lambda: self.set_filter("LOW_STOCK"))
            self.btn_low.pack(side="left", padx=5)
            self.btn_exp = ctk.CTkButton(filter_frame, text="⏳ Expiring", fg_color="#ffffff", text_color=TEXT_MAIN, border_width=1, width=90, height=35, hover_color="#f3f4f6", command=lambda: self.set_filter("EXPIRING"))
            self.btn_exp.pack(side="left", padx=5)
            ctk.CTkButton(filter_frame, text="🚚 Transfer", fg_color="#8b5cf6", hover_color="#7c3aed",
                          font=("Inter", 12, "bold"), height=35,
                          command=self.open_transfer_dialog).pack(side="left", padx=10)
        elif self.active_tab == "Warehouse":
            ctk.CTkButton(toolbar, text="➕ Add Warehouse", fg_color="#10b981", hover_color="#059669",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_add_warehouse_dialog).pack(side="right")
        elif self.active_tab == "Store":
            ctk.CTkButton(toolbar, text="➕ Add Store", fg_color="#10b981", hover_color="#059669",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_add_store_dialog).pack(side="right")
        elif self.active_tab == "Category":
            ctk.CTkButton(toolbar, text="➕ Add Category", fg_color="#10b981", hover_color="#059669",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_add_category_dialog).pack(side="right")

        table_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
        table_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        if self.active_tab == "Inventory":
            cols = ("ID", "Product", "Batch", "Location", "Quantity", "Exp Date", "Status")
            self.tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="extended")
            for col in cols:
                self.tree.heading(col, text=col.upper())
                self.tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=120 if col == "Location" else 100)
                if col == "ID": self.tree.column(col, width=50)
            # Heading có thể click để lọc theo khoảng (hiển thị icon khi đang filter)
            qty_on = self.range_filter["qty_min"] is not None or self.range_filter["qty_max"] is not None
            exp_on = self.range_filter["exp_from"] is not None or self.range_filter["exp_to"] is not None
            self.tree.heading("Quantity",
                              text="QUANTITY 🔍" if qty_on else "QUANTITY ▲▼",
                              command=self.open_qty_range_filter)
            self.tree.heading("Exp Date",
                              text="EXP DATE 🔍" if exp_on else "EXP DATE ▲▼",
                              command=self.open_exp_date_filter)
            self.tree.pack(fill="both", expand=True)

        elif self.active_tab == "Product":
            cols = ("ID", "Name", "Category ID", "Price", "Status")
            self.tree = ttk.Treeview(table_container, columns=cols, show="headings")
            for col in cols: self.tree.heading(col, text=col.upper())
            self.tree.bind("<Double-1>", self.on_product_double_click)
            self.tree.pack(fill="both", expand=True)

        elif self.active_tab == "Category":
            cols = ("ID", "Name")
            self.tree = ttk.Treeview(table_container, columns=cols, show="headings")
            for col in cols: self.tree.heading(col, text=col.upper())
            self.tree.bind("<Double-1>", self.on_category_double_click)
            self.tree.pack(fill="both", expand=True)

        elif self.active_tab == "Warehouse":
            cols = ("ID", "Name", "Capacity", "Total Batches", "Total Qty")
            self.tree = ttk.Treeview(table_container, columns=cols, show="headings")
            for col in cols:
                self.tree.heading(col, text=col.upper())
                self.tree.column(col, anchor="w" if col == "Name" else "center")
            self.tree.bind("<Double-1>", self.on_warehouse_double_click)
            self.tree.pack(fill="both", expand=True)

        elif self.active_tab == "Store":
            cols = ("ID", "Name", "Location", "Total Batches", "Total Qty")
            self.tree = ttk.Treeview(table_container, columns=cols, show="headings")
            for col in cols:
                self.tree.heading(col, text=col.upper())
                self.tree.column(col, anchor="w" if col in ("Name", "Location") else "center")
            self.tree.bind("<Double-1>", self.on_store_double_click)
            self.tree.pack(fill="both", expand=True)

        self.refresh_table()

    def on_category_double_click(self, event):
        try:
            selected_item = self.tree.selection()[0]
            cat_id = self.tree.item(selected_item)['values'][0]
            self.filter_category_id = str(cat_id)
            self.filter_product_id = None
            self.switch_tab("Product", clear_filter=False)
        except IndexError: pass

    def on_product_double_click(self, event):
        try:
            selected_item = self.tree.selection()[0]
            prod_id = self.tree.item(selected_item)['values'][0]
            self.filter_product_id = str(prod_id)
            self.filter_category_id = None
            self.filter_warehouse_id = None
            self.switch_tab("Inventory", clear_filter=False)
        except IndexError: pass

    def on_warehouse_double_click(self, event):
        try:
            selected_item = self.tree.selection()[0]
            wh_id = self.tree.item(selected_item)['values'][0]
            self.filter_warehouse_id = str(wh_id)
            self.filter_category_id = None
            self.filter_product_id = None
            self.switch_tab("Inventory", clear_filter=False)
        except IndexError: pass

    def on_store_double_click(self, event):
        try:
            selected_item = self.tree.selection()[0]
            store_id = self.tree.item(selected_item)['values'][0]
            self.filter_store_id = str(store_id)
            self.filter_category_id = None
            self.filter_product_id = None
            self.filter_warehouse_id = None
            self.switch_tab("Inventory", clear_filter=False)
        except IndexError: pass

    def clear_drilldown_filters(self):
        self.filter_category_id = None
        self.filter_product_id = None
        self.filter_warehouse_id = None
        self.filter_store_id = None
        self.build_main_content()

    def set_filter(self, filter_type):
        self.current_filter = filter_type
        for btn in [self.btn_all, self.btn_low, self.btn_exp]: btn.configure(fg_color="#ffffff", text_color=TEXT_MAIN, border_width=1)
        if filter_type == "ALL": self.btn_all.configure(fg_color=PRIMARY_COLOR, text_color="white", border_width=0)
        elif filter_type == "LOW_STOCK": self.btn_low.configure(fg_color="#f97316", text_color="white", border_width=0)
        elif filter_type == "EXPIRING": self.btn_exp.configure(fg_color="#ef4444", text_color="white", border_width=0)
        self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        keyword = self.search_var.get()
        
        if self.active_tab == "Inventory":
            qty_min = self.range_filter["qty_min"]
            qty_max = self.range_filter["qty_max"]
            exp_from = self.range_filter["exp_from"]
            exp_to   = self.range_filter["exp_to"]

            if self.current_filter == "LOW_STOCK":
                data = self.service.get_low_stock_items()
            elif self.current_filter == "EXPIRING":
                data = self.service.get_expiring_items()
            elif qty_min is not None or qty_max is not None:
                # Dùng BST range_search — O(log n + k), không cần duyệt toàn bộ
                lo = qty_min if qty_min is not None else 0
                hi = qty_max if qty_max is not None else 999_999
                bst_items = self.service.qty_bst.range_search(lo, hi)
                bst_ids = {inv.id for inv in bst_items}
                if keyword.strip():
                    data = [inv for inv in self.service.search_items(keyword, "Inventory")
                            if inv.id in bst_ids]
                else:
                    data = [inv for inv in self.service.inventory_map.values()
                            if inv.id in bst_ids]
            else:
                data = self.service.search_items(keyword, "Inventory")

            for inv in data:
                if self.filter_product_id and str(inv.product_id) != self.filter_product_id: continue
                if self.filter_warehouse_id and str(inv.warehouse_id) != self.filter_warehouse_id: continue
                if self.filter_store_id and str(inv.store_id) != self.filter_store_id: continue
                # Lọc theo khoảng ngày Exp Date
                if exp_from or exp_to:
                    try:
                        exp_d = (datetime.strptime(str(inv.exp_date), "%Y-%m-%d").date()
                                 if isinstance(inv.exp_date, str) else inv.exp_date)
                        if exp_from and exp_d < exp_from: continue
                        if exp_to   and exp_d > exp_to:   continue
                    except Exception:
                        pass
                prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
                status = "Low Stock" if inv.quantity <= self.service.settings["low_stock_threshold"] else "In Stock"
                
                loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
                
                self.tree.insert("", "end", values=(inv.id, prod_name, inv.batch_id, loc,
                                                    inv.quantity, inv.exp_date, status))

        elif self.active_tab == "Store":
            data = self.service.search_items(keyword, "Store")
            summary = self.service.get_store_summary()
            for st in data:
                stats = summary.get(st.id, {"batches": 0, "total_qty": 0})
                self.tree.insert("", "end", values=(st.id, st.name, st.location, stats["batches"], stats["total_qty"]))

        elif self.active_tab == "Product":
            data = self.service.search_items(keyword, "Product")
            for p in data:
                if self.filter_category_id and str(p.category_id) != self.filter_category_id: continue
                self.tree.insert("", "end", values=(p.id, p.name, p.category_id, f"${p.price}", getattr(p, 'status', 'Active')))
                
        elif self.active_tab == "Category":
            data = self.service.search_items(keyword, "Category")
            for c in data:
                self.tree.insert("", "end", values=(c.id, c.name))

        elif self.active_tab == "Warehouse":
            data = self.service.search_items(keyword, "Warehouse")
            wh_summary = self.service.get_warehouse_summary()
            for w in data:
                stats = wh_summary.get(w.id, {"batches": 0, "total_qty": 0})
                self.tree.insert("", "end", values=(
                    w.id, w.name, f"{w.space:,}",
                    stats["batches"], f"{stats['total_qty']:,}"
                ))

    def open_qty_range_filter(self):
        """Popup lọc theo khoảng Số lượng — sử dụng BST range_search"""
        d = ctk.CTkToplevel(self)
        d.title("Lọc theo Số lượng (BST Range Search)")
        d.geometry("340x240")
        d.resizable(False, False)
        d.attributes("-topmost", True)

        ctk.CTkLabel(d, text="🔢 Lọc Quantity theo khoảng",
                     font=("Inter", 14, "bold")).pack(pady=(18, 10))

        row = ctk.CTkFrame(d, fg_color="transparent")
        row.pack(padx=20)
        ctk.CTkLabel(row, text="Từ:", font=("Inter", 12)).pack(side="left", padx=(0, 6))
        min_ent = ctk.CTkEntry(row, width=90, placeholder_text="0")
        min_ent.pack(side="left", padx=(0, 16))
        if self.range_filter["qty_min"] is not None:
            min_ent.insert(0, str(self.range_filter["qty_min"]))

        ctk.CTkLabel(row, text="Đến:", font=("Inter", 12)).pack(side="left", padx=(0, 6))
        max_ent = ctk.CTkEntry(row, width=90, placeholder_text="9999")
        max_ent.pack(side="left")
        if self.range_filter["qty_max"] is not None:
            max_ent.insert(0, str(self.range_filter["qty_max"]))

        def apply_filter():
            try:
                mn = int(min_ent.get()) if min_ent.get().strip() else None
                mx = int(max_ent.get()) if max_ent.get().strip() else None
                self.range_filter["qty_min"] = mn
                self.range_filter["qty_max"] = mx
                self.build_main_content()   # rebuild để cập nhật icon heading
                d.destroy()
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số nguyên!", parent=d)

        def clear_filter():
            self.range_filter["qty_min"] = None
            self.range_filter["qty_max"] = None
            self.build_main_content()
            d.destroy()

        btn_row = ctk.CTkFrame(d, fg_color="transparent")
        btn_row.pack(pady=20)
        ctk.CTkButton(btn_row, text="✅ Áp dụng", fg_color=PRIMARY_COLOR,
                      width=120, command=apply_filter).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="❌ Xoá lọc", fg_color="#fee2e2", text_color="#b91c1c",
                      hover_color="#fca5a5", width=100, command=clear_filter).pack(side="left")

    def open_exp_date_filter(self):
        """Popup lọc theo khoảng Ngày hết hạn"""
        d = ctk.CTkToplevel(self)
        d.title("Lọc theo Ngày Hết hạn")
        d.geometry("380x230")
        d.resizable(False, False)
        d.attributes("-topmost", True)

        ctk.CTkLabel(d, text="📅 Lọc Exp Date theo khoảng",
                     font=("Inter", 14, "bold")).pack(pady=(18, 10))

        row = ctk.CTkFrame(d, fg_color="transparent")
        row.pack(padx=20)
        ctk.CTkLabel(row, text="Từ:", font=("Inter", 12)).pack(side="left", padx=(0, 6))
        from_picker = DateEntry(row, width=12, background=PRIMARY_COLOR,
                                foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
        from_picker.pack(side="left", padx=(0, 20))
        if self.range_filter["exp_from"]:
            from_picker.set_date(self.range_filter["exp_from"])

        ctk.CTkLabel(row, text="Đến:", font=("Inter", 12)).pack(side="left", padx=(0, 6))
        to_picker = DateEntry(row, width=12, background=PRIMARY_COLOR,
                              foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
        to_picker.pack(side="left")
        if self.range_filter["exp_to"]:
            to_picker.set_date(self.range_filter["exp_to"])

        def apply_filter():
            self.range_filter["exp_from"] = from_picker.get_date()
            self.range_filter["exp_to"]   = to_picker.get_date()
            self.build_main_content()
            d.destroy()

        def clear_filter():
            self.range_filter["exp_from"] = None
            self.range_filter["exp_to"]   = None
            self.build_main_content()
            d.destroy()

        btn_row = ctk.CTkFrame(d, fg_color="transparent")
        btn_row.pack(pady=20)
        ctk.CTkButton(btn_row, text="✅ Áp dụng", fg_color=PRIMARY_COLOR,
                      width=120, command=apply_filter).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="❌ Xoá lọc", fg_color="#fee2e2", text_color="#b91c1c",
                      hover_color="#fca5a5", width=100, command=clear_filter).pack(side="left")

    def open_add_category_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Category")
        dialog.geometry("420x220")
        dialog.attributes("-topmost", True)

        cat_id = self.service.generate_category_id()
        ctk.CTkLabel(dialog, text=f"Category ID (Auto): {cat_id}", font=("Inter", 12, "bold")).pack(pady=(20, 2), padx=20, anchor="w")

        ctk.CTkLabel(dialog, text="Category Name:", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        name_ent = ctk.CTkEntry(dialog, width=370, placeholder_text="VD: Mẹ và Bé")
        name_ent.pack(padx=20)

        def save_category():
            cat_name = name_ent.get().strip()
            if not cat_name:
                messagebox.showerror("Lỗi", "Tên danh mục không được để trống!", parent=dialog)
                return
            try:
                success = self.service.add_category(cat_id, cat_name, self.cursor, self.conn)
                if success:
                    self.history.push(AddCategoryCommand(cat_id, cat_name))
                    self._update_undo_redo_buttons()
                    self.refresh_table()
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Đã thêm danh mục '{cat_name}' thành công!")
                else:
                    messagebox.showerror("Lỗi", f"Lỗi tạo danh mục!", parent=dialog)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi: {e}", parent=dialog)

        ctk.CTkButton(dialog, text="Save Category", fg_color="#10b981", hover_color="#059669",
                      font=("Inter", 13, "bold"), command=save_category).pack(pady=25)

    def open_add_warehouse_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Warehouse")
        dialog.geometry("420x260")
        dialog.attributes("-topmost", True)

        wh_id = self.service.generate_warehouse_id()
        ctk.CTkLabel(dialog, text=f"Warehouse ID (Auto): {wh_id}", font=("Inter", 12, "bold")).pack(pady=(20, 2), padx=20, anchor="w")

        ctk.CTkLabel(dialog, text="Warehouse Name:", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        name_ent = ctk.CTkEntry(dialog, width=370, placeholder_text="VD: Warehouse D")
        name_ent.pack(padx=20)

        ctk.CTkLabel(dialog, text="Capacity (space):", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        space_ent = ctk.CTkEntry(dialog, width=370, placeholder_text="VD: 2000")
        space_ent.pack(padx=20)

        def save_warehouse():
            wh_name = name_ent.get().strip()
            wh_space = space_ent.get().strip()
            if not wh_name:
                messagebox.showerror("Lỗi", "Tên kho không được để trống!", parent=dialog)
                return
            try:
                space_val = int(wh_space) if wh_space else 0
                success = self.service.add_warehouse(wh_id, wh_name, space_val, self.cursor, self.conn)
                if success:
                    self.history.push(AddWarehouseCommand(wh_id, wh_name, space_val))
                    self._update_undo_redo_buttons()
                    self.build_kpi_cards()
                    self.refresh_table()
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Đã thêm kho '{wh_name}' thành công!")
                else:
                    messagebox.showerror("Lỗi", f"Warehouse ID '{wh_id}' đã tồn tại!", parent=dialog)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi: {e}", parent=dialog)

        ctk.CTkButton(dialog, text="Save Warehouse", fg_color="#10b981", hover_color="#059669",
                      font=("Inter", 13, "bold"), command=save_warehouse).pack(pady=25)


    def open_add_store_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Store")
        dialog.geometry("420x260")
        dialog.attributes("-topmost", True)

        st_id = self.service.generate_store_id()
        ctk.CTkLabel(dialog, text=f"Store ID (Auto): {st_id}", font=("Inter", 12, "bold")).pack(pady=(20, 2), padx=20, anchor="w")

        ctk.CTkLabel(dialog, text="Store Name:", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        name_ent = ctk.CTkEntry(dialog, width=370, placeholder_text="VD: Store Plaza")
        name_ent.pack(padx=20)

        ctk.CTkLabel(dialog, text="Location:", font=("Inter", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        loc_ent = ctk.CTkEntry(dialog, width=370, placeholder_text="VD: 789 West St")
        loc_ent.pack(padx=20)

        def save_store():
            st_name = name_ent.get().strip()
            st_loc = loc_ent.get().strip()
            if not st_name:
                messagebox.showerror("Lỗi", "Tên cửa hàng không được để trống!", parent=dialog)
                return
            try:
                success = self.service.add_store(st_id, st_name, st_loc, self.cursor, self.conn)
                if success:
                    self.history.push(AddStoreCommand(st_id, st_name, st_loc))
                    self._update_undo_redo_buttons()
                    self.build_kpi_cards()
                    self.refresh_table()
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Đã thêm cửa hàng '{st_name}' thành công!")
                else:
                    messagebox.showerror("Lỗi", f"Store ID '{st_id}' đã tồn tại!", parent=dialog)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi: {e}", parent=dialog)

        ctk.CTkButton(dialog, text="Save Store", fg_color="#10b981", hover_color="#059669",
                      font=("Inter", 13, "bold"), command=save_store).pack(pady=25)


    def open_transfer_dialog(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Vui lòng chọn 1 lô hàng từ Warehouse để luân chuyển!")
            return
        
        item_data = self.tree.item(selected[0])['values']
        item_id = item_data[0] # ID nằm ở cột đầu tiên
        # Lấy từ service
        source_item = self.service.inventory_map.get(item_id)
        if not source_item or not source_item.warehouse_id:
            messagebox.showwarning("Warning", "Chỉ có thể luân chuyển lô hàng từ Warehouse (Kho) xuống Store!")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Transfer to Store")
        dialog.geometry("400x350")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text=f"Transferring Batch: {source_item.batch_id}", font=("Inter", 13, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text=f"Available Quantity: {source_item.quantity}", font=("Inter", 12)).pack(pady=(0, 15))

        ctk.CTkLabel(dialog, text="Target Store ID:", font=("Inter", 12, "bold")).pack(anchor="w", padx=20)
        store_ids = list(self.service.stores_map.keys())
        if not store_ids:
            messagebox.showwarning("Warning", "Hệ thống chưa có Cửa hàng nào. Vui lòng thêm Store trước.")
            dialog.destroy()
            return
        
        store_cb = ctk.CTkComboBox(dialog, values=store_ids, width=360)
        store_cb.pack(padx=20, pady=(5, 15))

        ctk.CTkLabel(dialog, text="Quantity to Transfer:", font=("Inter", 12, "bold")).pack(anchor="w", padx=20)
        qty_ent = ctk.CTkEntry(dialog, width=360, placeholder_text=f"Max: {source_item.quantity}")
        qty_ent.pack(padx=20, pady=(5, 20))

        def confirm_transfer():
            target_store = store_cb.get()
            qty_str = qty_ent.get()
            if not qty_str.isdigit():
                messagebox.showerror("Lỗi", "Số lượng phải là số nguyên!", parent=dialog)
                return
            transfer_qty = int(qty_str)
            if transfer_qty <= 0 or transfer_qty > source_item.quantity:
                messagebox.showerror("Lỗi", "Số lượng không hợp lệ!", parent=dialog)
                return
            
            try:
                success, new_item_id = self.service.transfer_inventory(source_item.id, target_store, transfer_qty, self.cursor, self.conn)
                if success:
                    # Truyền Undo/Redo command
                    self.history.push(TransferInventoryCommand(
                        source_item_id=source_item.id,
                        target_item_id=new_item_id,
                        target_store_id=target_store,
                        transfer_qty=transfer_qty
                    ))
                    self._update_undo_redo_buttons()
                    self.refresh_table()
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Đã luân chuyển {transfer_qty} sản phẩm sang Store '{target_store}'!")
                else:
                    messagebox.showerror("Lỗi", "Chuyển kho thất bại!", parent=dialog)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi transfer: {e}", parent=dialog)

        ctk.CTkButton(dialog, text="Confirm Transfer", fg_color="#8b5cf6", hover_color="#7c3aed",
                      font=("Inter", 13, "bold"), command=confirm_transfer).pack(pady=10)
    # UNDO / REDO
    # ==========================================
    def do_undo(self):
        if not self.history.can_undo():
            return
        desc = self.history.peek_undo()
        try:
            self.history.undo(self.service, self.cursor, self.conn)
            self.build_kpi_cards()
            self.refresh_table()
            self._update_undo_redo_buttons()
            messagebox.showinfo("Undo", f"✅ Đã hoàn tác:\n{desc}")
        except Exception as e:
            messagebox.showerror("Undo Error", f"Không thể hoàn tác: {e}")

    def do_redo(self):
        if not self.history.can_redo():
            return
        desc = self.history.peek_redo()
        try:
            self.history.redo(self.service, self.cursor, self.conn)
            self.build_kpi_cards()
            self.refresh_table()
            self._update_undo_redo_buttons()
            messagebox.showinfo("Redo", f"✅ Đã làm lại:\n{desc}")
        except Exception as e:
            messagebox.showerror("Redo Error", f"Không thể làm lại: {e}")

    def _update_undo_redo_buttons(self):
        """Cập nhật trạng thái nút Undo/Redo và tooltip mô tả lệnh"""
        if self.history.can_undo():
            self.btn_undo.configure(state="normal", text_color=TEXT_MAIN,
                                    text=f"↩ Undo")
        else:
            self.btn_undo.configure(state="disabled", text_color="#9ca3af",
                                    text="↩ Undo")
        if self.history.can_redo():
            self.btn_redo.configure(state="normal", text_color=TEXT_MAIN,
                                    text=f"↪ Redo")
        else:
            self.btn_redo.configure(state="disabled", text_color="#9ca3af",
                                    text="↪ Redo")


if __name__ == "__main__":
    app = App()
    app.mainloop()