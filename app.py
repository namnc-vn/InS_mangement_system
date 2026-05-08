import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry # <--- THƯ VIỆN LỊCH
from service import Service
from history import (CommandHistory, AddBatchCommand, UpdateBatchQtyCommand,
                      AddProductCommand, AddCategoryCommand, AddWarehouseCommand,
                      AddStoreCommand, TransferBatchCommand)
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
        self.title("Batch and Store management")
        self.geometry("1250x800")
        self.configure(fg_color=BG_APP)

        self.conn = None
        self.service = None
        self.history = CommandHistory()
        try:
            self.conn = db_connect.get_connection()
            self.service = Service(self.conn)
            self.service.load_data()
        except Exception as e:
            messagebox.showwarning("Lỗi Database", f"Chạy offline mode. Lỗi DB: {e}")
            self.service = Service()

        self.active_tab = "Category" 
        self.current_filter = "ALL"
        self.filter_category_id = None
        self.filter_product_id = None
        self.filter_warehouse_id = None
        self.filter_store_id = None
        # Lọc theo khoảng — Quantity (BST) & Exp Date
        self.range_filter = {"qty_min": None, "qty_max": None,
                             "exp_from": None, "exp_to": None}
        # Checkbox tracking cho Category & Product
        self.selected_categories = set()  # {cat_id}
        self.selected_products = set()    # {prod_id}

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
        style.theme_use("clam")
        style.configure("Treeview", background=BG_CARD, foreground=TEXT_MAIN, rowheight=40,
                        fieldbackground=BG_CARD, borderwidth=0, font=("Inter", 11))
        style.configure("Treeview.Heading", background=BG_CARD, foreground=TEXT_SUB,
                        font=("Inter", 10, "bold"), borderwidth=0)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.map("Treeview", background=[("selected", "#e0e7ff"), ("!selected", BG_CARD)],
                  foreground=[("selected", PRIMARY_COLOR)])

    # ==========================================
    # HEADER & THÊM MỚI (TÍCH HỢP TRIE & CALENDAR)
    # ==========================================
    def build_top_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.header_frame.pack(fill="x", padx=30, pady=(20, 10))

        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="Batch and Store Management", font=("Inter", 24, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
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

        ctk.CTkButton(self.header_frame, text="➕ New Batch", fg_color=PRIMARY_COLOR, hover_color="#2563eb",
                      font=("Inter", 13, "bold"), height=40, command=self.open_add_batch_dialog).pack(side="right", padx=6)

    def open_add_batch_dialog(self):
        """Hộp thoại thêm tồn kho — Autocomplete thực sự với Entry + Listbox nổi"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Batch")
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
                     or list(set(inv.warehouse_id for inv in self.service.batch_map.values() if inv.warehouse_id))
                     or ["WH-A", "WH-B"])
        wh_cb = ctk.CTkComboBox(dialog, width=470, values=wh_values, font=("Inter", 12))
        wh_cb.pack(padx=20)
        if wh_values:
            wh_cb.set(wh_values[0])

        def save_batch():
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
                existing = self.service.check_batch_exist(p_id, b_id, mfg, exp, wh)
                old_qty  = existing.quantity if existing else None
                old_batch_id   = existing.batch_id if existing else None

                entry_date = mfg  # Assume entry_date = mfg_date
                self.service.add_batch_item(p_id, qty, b_id, mfg, exp, entry_date, wh)

                # Tạo và đẩy Command vào history
                if old_qty is not None:
                    cmd = UpdateBatchQtyCommand(old_batch_id, old_qty, qty)
                else:
                    comp_key = (p_id, b_id, mfg, exp, wh)
                    new_item = self.service.batch_composite_map.get(comp_key)
                    cmd = AddBatchCommand(new_item.batch_id, p_id, mfg, exp, entry_date, qty, wh)
                self.history.push(cmd)
                self._update_undo_redo_buttons()

                self.build_kpi_cards()
                self.refresh_table()
                dialog.destroy()
                messagebox.showinfo("Success", "Thêm tồn kho thành công!")
            except Exception as e:
                messagebox.showerror("Error", f"Lỗi nhập liệu/CSDL: {e}")

        ctk.CTkButton(dialog, text="💾 Save Batch", fg_color=PRIMARY_COLOR,
                      hover_color="#2563eb", font=("Inter", 13, "bold"),
                      height=42, width=470, command=save_batch).pack(pady=18, padx=20)

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
                success = self.service.add_product(p_id, p_name, cat_id, price, status)
                if success:
                    self.history.push(AddProductCommand(p_id, p_name, cat_id, price, status))
                    self._update_undo_redo_buttons()
                    messagebox.showinfo("Success", "Sản phẩm đã tạo thành công! Bạn có thể lưu Batch.")
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
            {"title": "Stores", "key": "Stores", "icon": "🏬", "bg_icon": "#f0f9ff", "icon_color": "#0c4a6e"}
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

        alert_card.bind("<Button-1>", lambda e: self.open_warning_dialog())
        top_alert.bind("<Button-1>", lambda e: self.open_warning_dialog())
        bot_alert.bind("<Button-1>", lambda e: self.open_warning_dialog())

    def open_warning_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Batch Alerts")
        dialog.geometry("940x560")
        dialog.attributes("-topmost", True)

        header = ctk.CTkLabel(dialog, text="Batch Alerts", font=("Inter", 20, "bold"), text_color=TEXT_MAIN)
        header.pack(anchor="w", padx=24, pady=(20, 10))

        desc = ctk.CTkLabel(dialog, text="Danh sách hàng sắp hết hạn và hàng tồn kho thấp", font=("Inter", 13), text_color=TEXT_SUB)
        desc.pack(anchor="w", padx=24, pady=(0, 20))

        content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        low_frame = ctk.CTkFrame(content_frame, fg_color="#fef7ed", corner_radius=14, border_width=1, border_color="#fcd34d")
        low_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        exp_frame = ctk.CTkFrame(content_frame, fg_color="#fef2f2", corner_radius=14, border_width=1, border_color="#fca5a5")
        exp_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)

        ctk.CTkLabel(low_frame, text=f"⚠️ Low Stock ({len(self.service.get_low_stock_items())})", font=("Inter", 16, "bold"), text_color="#c2410c").pack(anchor="w", padx=20, pady=(20, 10))
        low_tree = ttk.Treeview(low_frame, columns=("Product", "SKU", "Location", "Quantity", "Threshold"), show="headings", height=8)
        for col in ("Product", "SKU", "Location", "Quantity", "Threshold"):
            low_tree.heading(col, text=col)
            low_tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=120)
        low_tree.tag_configure("lowstock", background="#fff7ed", foreground="#b45309")
        low_tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        exp_items = self.service.get_expiring_items()
        ctk.CTkLabel(exp_frame, text=f"⏳ Expiring Soon ({len(exp_items)})", font=("Inter", 16, "bold"), text_color="#b91c1c").pack(anchor="w", padx=20, pady=(20, 10))
        exp_tree = ttk.Treeview(exp_frame, columns=("Product", "SKU", "Location", "Quantity", "Exp Date", "Remaining"), show="headings", height=8)
        for col in ("Product", "SKU", "Location", "Quantity", "Exp Date", "Remaining"):
            exp_tree.heading(col, text=col)
            exp_tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=120)
        exp_tree.tag_configure("expired", background="#fee2e2", foreground="#991b1b")
        exp_tree.tag_configure("expiring", background="#fed7aa", foreground="#c2410c")
        exp_tree.tag_configure("warning", background="#fef3c7", foreground="#92400e")
        exp_tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        low_stock_threshold = self.service.settings.get("low_stock_threshold", 10)
        for inv in self.service.get_low_stock_items():
            prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
            loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
            low_tree.insert("", "end", values=(prod_name, inv.batch_id, loc, inv.quantity, low_stock_threshold), tags=("lowstock",))

        from datetime import datetime, date as date_type
        today = datetime.today().date()
        for inv in exp_items:
            prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
            loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
            exp_date = inv.exp_date
            if isinstance(exp_date, str):
                try:
                    exp_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
                except Exception:
                    exp_date = exp_date
            days_left = (exp_date - today).days if isinstance(exp_date, date_type) else "?"
            remaining = f"{days_left} ngày" if isinstance(days_left, int) else str(days_left)
            if isinstance(days_left, int):
                if days_left < 0:
                    tag = "expired"
                elif days_left <= 7:
                    tag = "expiring"
                else:
                    tag = "warning"
            else:
                tag = "warning"
            exp_tree.insert("", "end", values=(prod_name, inv.batch_id, loc, inv.quantity, exp_date, remaining), tags=(tag,))

        ctk.CTkButton(dialog, text="Đóng", fg_color="#6b7280", hover_color="#525252", command=dialog.destroy).pack(pady=16)

    def build_tabs(self):
        tab_frame = ctk.CTkFrame(self, fg_color="transparent", height=45)
        tab_frame.pack(fill="x", padx=38, pady=0)
        self.tab_btns = {}
        tabs = [("🏷️ Category", "Category"), ("📦 Product", "Product"), ("🏢 Warehouse", "Warehouse"), ("🏪 Store", "Store")]
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

        if self.active_tab == "Category":
            button_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
            button_frame.pack(side="right")
            ctk.CTkButton(button_frame, text="📋 Show Batch", fg_color="#8b5cf6", hover_color="#7c3aed",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_batch_dialog_for_categories).pack(side="left", padx=5)
            ctk.CTkButton(button_frame, text="➕ Add Category", fg_color="#10b981", hover_color="#059669",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_add_category_dialog).pack(side="left", padx=5)
        elif self.active_tab == "Product":
            button_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
            button_frame.pack(side="right")
            ctk.CTkButton(button_frame, text="📋 Show Batch", fg_color="#8b5cf6", hover_color="#7c3aed",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_batch_dialog_for_products).pack(side="left", padx=5)
        elif self.active_tab == "Warehouse":
            ctk.CTkButton(toolbar, text="➕ Add Warehouse", fg_color="#10b981", hover_color="#059669",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_add_warehouse_dialog).pack(side="right")
        elif self.active_tab == "Store":
            ctk.CTkButton(toolbar, text="➕ Add Store", fg_color="#10b981", hover_color="#059669",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_add_store_dialog).pack(side="right")

        table_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
        table_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        if self.active_tab == "Product":
            cols = ("✓", "ID", "Name", "Category ID", "Price", "Status")
            self.tree = ttk.Treeview(table_container, columns=cols, show="headings")
            self.tree.heading("✓", text="✓")
            self.tree.column("✓", width=30, anchor="center")
            for col in cols[1:]:
                self.tree.heading(col, text=col.upper())
            self.tree.bind("<Double-1>", self.on_product_double_click)
            self.tree.bind("<Button-1>", self.on_tree_click_product_checkbox)
            self.tree.pack(fill="both", expand=True)

        elif self.active_tab == "Category":
            cols = ("✓", "ID", "Name")
            self.tree = ttk.Treeview(table_container, columns=cols, show="headings")
            self.tree.heading("✓", text="✓")
            self.tree.column("✓", width=30, anchor="center")
            for col in cols[1:]:
                self.tree.heading(col, text=col.upper())
            self.tree.bind("<Double-1>", self.on_category_double_click)
            self.tree.bind("<Button-1>", self.on_tree_click_category_checkbox)
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
            values = self.tree.item(selected_item)['values']
            cat_id = values[1] if len(values) > 1 else values[0]
            self.filter_category_id = str(cat_id)
            self.filter_product_id = None
            self.switch_tab("Product", clear_filter=False)
        except IndexError: pass

    def on_product_double_click(self, event):
        try:
            selected_item = self.tree.selection()[0]
            values = self.tree.item(selected_item)['values']
            prod_id = values[1] if len(values) > 1 else values[0]
            self.selected_products = {str(prod_id)}
            self.open_batch_dialog_for_products()
        except IndexError: pass

    def on_tree_click_category_checkbox(self, event):
        """Handle checkbox click in Category treeview"""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        col = self.tree.identify_column(event.x)
        if col != "#1":  # Column 1 is the checkbox column
            return
        
        row = self.tree.identify_row(event.y)
        if not row:
            return
        
        # Get the category ID (column 1, which is index 1 in values)
        values = self.tree.item(row)['values']
        cat_id = str(values[1])  # Column "ID" is at index 1
        
        # Toggle checkbox
        if cat_id in self.selected_categories:
            self.selected_categories.discard(cat_id)
        else:
            self.selected_categories.add(cat_id)
        
        # Update display - re-render the checkbox column
        self.tree.item(row, values=(
            "✓" if cat_id in self.selected_categories else "☐",
            values[1], values[2]
        ))

    def on_tree_click_product_checkbox(self, event):
        """Handle checkbox click in Product treeview"""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        col = self.tree.identify_column(event.x)
        if col != "#1":  # Column 1 is the checkbox column
            return
        
        row = self.tree.identify_row(event.y)
        if not row:
            return
        
        # Get the product ID (column 1, which is index 1 in values)
        values = self.tree.item(row)['values']
        prod_id = str(values[1])  # Column "ID" is at index 1
        
        # Toggle checkbox
        if prod_id in self.selected_products:
            self.selected_products.discard(prod_id)
        else:
            self.selected_products.add(prod_id)
        
        # Update display - re-render the checkbox column
        self.tree.item(row, values=(
            "✓" if prod_id in self.selected_products else "☐",
            values[1], values[2], values[3], values[4], values[5]
        ))
    
    def on_warehouse_double_click(self, event):
        try:
            selected_item = self.tree.selection()[0]
            wh_id = self.tree.item(selected_item)['values'][0]
            # Load and display batch for warehouse
            batch_items = [inv for inv in self.service.batch_map.values() 
                             if str(inv.warehouse_id) == str(wh_id)]
            if not batch_items:
                messagebox.showinfo("Info", f"No batch found in Warehouse {wh_id}", parent=self)
                return
            self._show_batch_dialog("Warehouse Batch", batch_items)
        except IndexError: pass

    def on_store_double_click(self, event):
        try:
            selected_item = self.tree.selection()[0]
            store_id = self.tree.item(selected_item)['values'][0]
            # Load and display batch for store
            batch_items = [inv for inv in self.service.batch_map.values() 
                             if str(inv.store_id) == str(store_id)]
            if not batch_items:
                messagebox.showinfo("Info", f"No batch found in Store {store_id}", parent=self)
                return
            self._show_batch_dialog("Store Batch", batch_items)
        except IndexError: pass

    def _format_batch_status(self, inv, low_stock_threshold):
        status = "Low Stock" if inv.quantity <= low_stock_threshold else "In Stock"
        exp_date = inv.exp_date
        days_left = None
        if isinstance(exp_date, str):
            try:
                exp_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
            except Exception:
                exp_date = exp_date
        if isinstance(exp_date, date_type):
            days_left = (exp_date - datetime.today().date()).days

        if isinstance(days_left, int) and days_left < 0:
            return "🔴 Expired"
        if isinstance(days_left, int) and days_left <= 7:
            return "🟠 Expiring"
        if isinstance(days_left, int) and days_left <= 30:
            return "🟡 Warning"
        if status == "Low Stock":
            return "🟡 Low Stock"
        return "🟢 In Stock"

    def _format_batch_status_and_tag(self, inv, low_stock_threshold):
        status_text = self._format_batch_status(inv, low_stock_threshold)
        if status_text.startswith("🔴"):
            return status_text, "expired"
        if status_text.startswith("🟠"):
            return status_text, "expiring"
        if status_text.startswith("🟡") and "Warning" in status_text:
            return status_text, "warning"
        if status_text.startswith("🟡") and "Low Stock" in status_text:
            return status_text, "lowstock"
        return status_text, "instock"

    def _show_batch_dialog(self, title, batch_items):
        """Generic dialog to show batch items"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("900x500")
        dialog.attributes("-topmost", True)
        
        if not batch_items:
            ctk.CTkLabel(dialog, text="No batch found", 
                        font=("Inter", 12)).pack(pady=20)
            return
        
        # Treeview để hiển thị batch
        cols = ("Batch ID", "Product", "MFG Date", "Quantity", "Location", "Exp Date", "Entry Date", "Status")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=20)
        for col in cols:
            tree.heading(col, text=col.upper())
            tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=100)
        
        tree.tag_configure("instock", foreground="#0f766e", background="#ecfdf5")
        tree.tag_configure("lowstock", foreground="#78350f", background="#fef3c7")
        tree.tag_configure("expired", foreground="#7f1d1d", background="#fee2e2")
        tree.tag_configure("expiring", foreground="#9a3412", background="#ffedd5")
        tree.tag_configure("warning", foreground="#92400e", background="#fef9c3")
        
        # Thêm data
        low_stock_threshold = self.service.settings.get("low_stock_threshold", 10)
        for inv in batch_items:
            prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
            status_text, status_tag = self._format_batch_status_and_tag(inv, low_stock_threshold)
            loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
            tree.insert("", "end", values=(inv.batch_id, prod_name, inv.mfg_date, inv.quantity, loc, inv.exp_date, inv.entry_date, status_text), tags=(status_tag,))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
    
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
        
        if self.active_tab == "Store":
            data = self.service.search_items(keyword, "Store")
            summary = self.service.get_store_summary()
            for st in data:
                stats = summary.get(st.id, {"batches": 0, "total_qty": 0})
                self.tree.insert("", "end", values=(st.id, st.name, st.location, stats["batches"], stats["total_qty"]))

        elif self.active_tab == "Product":
            data = self.service.search_items(keyword, "Product")
            for p in data:
                if self.filter_category_id and str(p.category_id) != self.filter_category_id: continue
                checkbox = "✓" if str(p.id) in self.selected_products else "☐"
                self.tree.insert("", "end", values=(checkbox, p.id, p.name, p.category_id, f"${p.price}", getattr(p, 'status', 'Active')))
                
        elif self.active_tab == "Category":
            data = self.service.search_items(keyword, "Category")
            for c in data:
                checkbox = "✓" if str(c.id) in self.selected_categories else "☐"
                self.tree.insert("", "end", values=(checkbox, c.id, c.name))

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
                success = self.service.add_category(cat_id, cat_name)
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
                success = self.service.add_warehouse(wh_id, wh_name, space_val)
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
                success = self.service.add_store(st_id, st_name, st_loc)
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
        source_item = self.service.batch_map.get(item_id)
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
                success, new_batch_id = self.service.transfer_batch(source_item.batch_id, target_store, transfer_qty)
                if success:
                    # Truyền Undo/Redo command
                    self.history.push(TransferBatchCommand(
                        source_batch_id=source_item.batch_id,
                        target_batch_id=new_batch_id,
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

    def open_batch_dialog_for_categories(self):
        """Hiển thị hộp thoại batch của các category được chọn"""
        if not self.selected_categories:
            messagebox.showwarning("Warning", "Vui lòng chọn ít nhất một category (checkbox ✓)", parent=self)
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Batch by Category")
        dialog.geometry("900x500")
        dialog.attributes("-topmost", True)
        
        # Tổng hợp batch của các category được chọn
        all_batch = []
        for cat_id in self.selected_categories:
            products = [p for p in self.service.products_map.values() 
                       if str(p.category_id) == str(cat_id)]
            for prod in products:
                batch_items = self.service.load_product_batch(prod.id)
                all_batch.extend(batch_items if batch_items else [])
        
        if not all_batch:
            ctk.CTkLabel(dialog, text="No batch found for selected categories", 
                        font=("Inter", 12)).pack(pady=20)
            return
        
        # Treeview để hiển thị batch
        cols = ("Batch ID", "Product", "MFG Date", "Quantity", "Location", "Exp Date", "Entry Date", "Status")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=20)
        for col in cols:
            tree.heading(col, text=col.upper())
            tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=100)
        tree.tag_configure("instock", foreground="#0f766e", background="#ecfdf5")
        tree.tag_configure("lowstock", foreground="#78350f", background="#fef3c7")
        tree.tag_configure("expired", foreground="#7f1d1d", background="#fee2e2")
        tree.tag_configure("expiring", foreground="#9a3412", background="#ffedd5")
        tree.tag_configure("warning", foreground="#92400e", background="#fef9c3")
        
        # Thêm data
        low_stock_threshold = self.service.settings.get("low_stock_threshold", 10)
        for inv in all_batch:
            prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
            status_text, status_tag = self._format_batch_status_and_tag(inv, low_stock_threshold)
            loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
            tree.insert("", "end", values=(inv.batch_id, prod_name, inv.mfg_date, inv.quantity, loc, inv.exp_date, inv.entry_date, status_text), tags=(status_tag,))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)

    def open_batch_dialog_for_products(self):
        """Hiển thị hộp thoại batch của các product được chọn"""
        if not self.selected_products:
            messagebox.showwarning("Warning", "Vui lòng chọn ít nhất một product (checkbox ✓)", parent=self)
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Batch by Product")
        dialog.geometry("900x500")
        dialog.attributes("-topmost", True)
        
        # Tổng hợp batch của các product được chọn
        all_batch = []
        for prod_id in self.selected_products:
            batch_items = self.service.load_product_batch(prod_id)
            all_batch.extend(batch_items if batch_items else [])
        
        if not all_batch:
            ctk.CTkLabel(dialog, text="No batch found for selected products", 
                        font=("Inter", 12)).pack(pady=20)
            return
        
        # Treeview để hiển thị batch
        cols = ("Batch ID", "Product", "MFG Date", "Quantity", "Location", "Exp Date", "Entry Date", "Status")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=20)
        for col in cols:
            tree.heading(col, text=col.upper())
            tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=100)
        tree.tag_configure("instock", foreground="#0f766e", background="#ecfdf5")
        tree.tag_configure("lowstock", foreground="#78350f", background="#fef3c7")
        tree.tag_configure("expired", foreground="#7f1d1d", background="#fee2e2")
        tree.tag_configure("expiring", foreground="#9a3412", background="#ffedd5")
        tree.tag_configure("warning", foreground="#92400e", background="#fef9c3")
        
        # Thêm data
        low_stock_threshold = self.service.settings.get("low_stock_threshold", 10)
        for inv in all_batch:
            prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
            status_text, status_tag = self._format_batch_status_and_tag(inv, low_stock_threshold)
            loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
            tree.insert("", "end", values=(inv.batch_id, prod_name, inv.mfg_date, inv.quantity, loc, inv.exp_date, inv.entry_date, status_text), tags=(status_tag,))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
    
    # UNDO / REDO
    # ==========================================
    def do_undo(self):
        if not self.history.can_undo():
            return
        desc = self.history.peek_undo()
        try:
            self.history.undo(self.service)
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
            self.history.redo(self.service)
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