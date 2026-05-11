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
        # Header filters cho Product tab
        self.product_column_filters = None

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
                        fieldbackground=BG_CARD, borderwidth=0, font=("Inter", 11, "bold"))
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
        ctk.CTkLabel(title_box, text="Warehouse Management", font=("Inter", 24, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="App quản lý kho hàng và cửa hàng", font=("Inter", 13, "bold"), text_color=TEXT_SUB).pack(anchor="w")

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

        ctk.CTkButton(self.header_frame, text="📋 Tasks", fg_color="#f3f4f6", text_color=TEXT_MAIN,
                      hover_color="#e5e7eb", font=("Inter", 13, "bold"), height=40,
                      command=self.open_task_manager_dialog).pack(side="right", padx=6)

        ctk.CTkButton(self.header_frame, text="📈 Reports", fg_color="#f3f4f6", text_color=TEXT_MAIN,
                      hover_color="#e5e7eb", font=("Inter", 13, "bold"), height=40,
                      command=self.open_reports_dialog).pack(side="right", padx=6)

        ctk.CTkButton(self.header_frame, text="⏰ History", fg_color="#f3f4f6", text_color=TEXT_MAIN,
                      hover_color="#e5e7eb", font=("Inter", 13, "bold"), height=40,
                      command=self.open_history_dialog).pack(side="right", padx=6)

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
                                 font=("Inter", 12, "bold"))
            entry.pack(padx=20)

            # --- Listbox nổi (floating popup) ---
            popup = tk.Frame(dialog, bg="white", relief="solid", bd=1)
            lb = tk.Listbox(popup, height=6, font=("Inter", 11, "bold"),
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
        qty_ent = ctk.CTkEntry(dialog, width=470, height=38, font=("Inter", 12, "bold"))
        qty_ent.pack(padx=20)

        # 3.5. Unit Price
        ctk.CTkLabel(dialog, text="Unit Price:",
                     font=("Inter", 12, "bold")).pack(pady=(14, 2), padx=20, anchor="w")
        price_ent = ctk.CTkEntry(dialog, width=470, height=38, font=("Inter", 12, "bold"))
        price_ent.pack(padx=20)
        price_ent.insert(0, "0")  # Default value

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
        wh_cb = ctk.CTkComboBox(dialog, width=470, values=wh_values, font=("Inter", 12, "bold"))
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
                unit_price = float(price_ent.get() or 0)
                # Kiểm tra trước để biết là Update hay Insert (phục vụ Undo)
                existing = self.service.check_batch_exist(p_id, b_id, mfg, exp, wh)
                old_qty  = existing.quantity if existing else None
                old_batch_id   = existing.batch_id if existing else None

                entry_date = mfg  # Assume entry_date = mfg_date
                self.service.add_batch_item(p_id, qty, b_id, mfg, exp, entry_date, wh, unit_price=unit_price)

                # Tạo và đẩy Command vào history
                if old_qty is not None:
                    cmd = UpdateBatchQtyCommand(old_batch_id, old_qty, qty)
                else:
                    comp_key = (p_id, b_id, mfg, exp, wh)
                    new_item = self.service.batch_composite_map.get(comp_key)
                    cmd = AddBatchCommand(new_item.batch_id, p_id, mfg, exp, entry_date, qty, unit_price, wh)
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
        dialog.geometry("400x400")
        dialog.attributes("-topmost", True)
        
        ctk.CTkLabel(dialog, text="Ngưỡng Số lượng thấp (Low Stock):", font=("Inter", 12, "bold")).pack(pady=(20, 5), padx=20, anchor="w")
        low_entry = ctk.CTkEntry(dialog, width=360)
        low_entry.insert(0, str(self.service.settings["low_stock_threshold"]))
        low_entry.pack(padx=20)
        
        ctk.CTkLabel(dialog, text="Ngưỡng Hết hạn (Ngày):", font=("Inter", 12, "bold")).pack(pady=(20, 5), padx=20, anchor="w")
        exp_entry = ctk.CTkEntry(dialog, width=360)
        exp_entry.insert(0, str(self.service.settings["expiring_days_threshold"]))
        exp_entry.pack(padx=20)

        ctk.CTkLabel(dialog, text="Ngưỡng Tồn lâu (Ngày):", font=("Inter", 12, "bold")).pack(pady=(20, 5), padx=20, anchor="w")
        aging_entry = ctk.CTkEntry(dialog, width=360)
        aging_entry.insert(0, str(self.service.settings["aging_days_threshold"]))
        aging_entry.pack(padx=20)
        
        def save():
            self.service.settings["low_stock_threshold"] = int(low_entry.get())
            self.service.settings["expiring_days_threshold"] = int(exp_entry.get())
            self.service.settings["aging_days_threshold"] = int(aging_entry.get())
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
            ctk.CTkLabel(info_frame, text=cfg["title"], font=("Inter", 13, "bold"), text_color=TEXT_SUB).pack(anchor="w")
            ctk.CTkLabel(info_frame, text=stats[cfg["key"]]["value"], font=("Inter", 26, "bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(5,0))
            ctk.CTkLabel(info_frame, text=stats[cfg["key"]]["trend"], font=("Inter", 12, "bold"), text_color="#10b981").pack(anchor="w")

            icon_box = ctk.CTkFrame(card, fg_color=cfg["bg_icon"], width=45, height=45, corner_radius=10)
            icon_box.pack(side="right", padx=20)
            icon_box.pack_propagate(False)
            ctk.CTkLabel(icon_box, text=cfg["icon"], font=("Inter", 20, "bold"), text_color=cfg["icon_color"]).place(relx=0.5, rely=0.5, anchor="center")

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

    def open_history_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Lịch sử giao dịch")
        dialog.geometry("980x700")
        dialog.attributes("-topmost", True)

        header = ctk.CTkLabel(dialog, text="📜 Lịch sử giao dịch", font=("Inter", 20, "bold"), text_color=TEXT_MAIN)
        header.pack(anchor="w", padx=24, pady=(20, 10))

        desc = ctk.CTkLabel(dialog, text="Lưu lại lịch sử nhập kho và chuyển kho. Lọc theo thời gian, sản phẩm, kho.", font=("Inter", 13, "bold"), text_color=TEXT_SUB)
        desc.pack(anchor="w", padx=24, pady=(0, 20))

        filter_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        filter_frame.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(filter_frame, text="Từ ngày:", font=("Inter", 12, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        start_date = DateEntry(filter_frame, date_pattern="yyyy-mm-dd", width=14)
        start_date.grid(row=0, column=1, padx=(0, 20), pady=4)

        ctk.CTkLabel(filter_frame, text="Đến ngày:", font=("Inter", 12, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        end_date = DateEntry(filter_frame, date_pattern="yyyy-mm-dd", width=14)
        end_date.grid(row=0, column=3, padx=(0, 20), pady=4)

        # Nút "Xem" để load lại dữ liệu theo ngày đã chọn
        ctk.CTkButton(filter_frame, text="Xem", width=60, fg_color=PRIMARY_COLOR, 
                      hover_color="#2563eb", font=("Inter", 12, "bold"), 
                      command=lambda: refresh_history()).grid(row=0, column=4, padx=(0, 10), pady=4)

        # Hàm xử lý cho nút All Time (Lấy mốc thời gian từ năm 2000 đến hiện tại)
        def set_all_time():
            start_date.set_date(datetime(2000, 1, 1).date()) 
            end_date.set_date(datetime.now().date())
            refresh_history()

        # Nút "All Time"
        ctk.CTkButton(filter_frame, text="All Time", width=80, fg_color="#10b981", 
                      hover_color="#059669", font=("Inter", 12, "bold"), 
                      command=set_all_time).grid(row=0, column=5, padx=(0, 20), pady=4)
        # -----------------------------

        ctk.CTkLabel(filter_frame, text="Sản phẩm:", font=("Inter", 12, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        product_options = ["ALL"] + [f"{p.id} - {p.name}" for p in self.service.products_map.values()]
        product_cb = ctk.CTkComboBox(filter_frame, values=product_options, width=280)
        product_cb.grid(row=1, column=1, columnspan=3, sticky="w", padx=(0, 20), pady=4)
        product_cb.set("ALL")

        ctk.CTkLabel(filter_frame, text="Kho:", font=("Inter", 12, "bold")).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        warehouse_options = ["ALL"] + list(self.service.warehouses_map.keys())
        warehouse_cb = ctk.CTkComboBox(filter_frame, values=warehouse_options, width=280)
        warehouse_cb.grid(row=2, column=1, columnspan=3, sticky="w", padx=(0, 20), pady=4)
        warehouse_cb.set("ALL")

        tree_frame = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color="#e5e7eb")
        tree_frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        cols = ("Time", "Action", "Product", "Batch", "Qty", "Source", "Target", "Notes")
        history_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        for col in cols:
            history_tree.heading(col, text=col)
            history_tree.column(col, anchor="center" if col in ("Time", "Action", "Qty") else "w", width=120)
        history_tree.column("Notes", width=220)
        history_tree.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        recent_frame = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color="#e5e7eb")
        recent_frame.pack(fill="x", expand=False, padx=24, pady=(0, 16))

        recent_header = ctk.CTkLabel(recent_frame, text="🕘 Sản phẩm vừa xem", font=("Inter", 16, "bold"), text_color=TEXT_MAIN)
        recent_header.pack(anchor="w", padx=20, pady=(16, 6))

        recent_tree = ttk.Treeview(recent_frame, columns=("ID", "Name", "Category", "Price", "Status"), show="headings", height=5)
        for col in ("ID", "Name", "Category", "Price", "Status"):
            recent_tree.heading(col, text=col)
            recent_tree.column(col, anchor="center" if col in ("ID", "Price", "Status") else "w", width=120)
        recent_tree.pack(fill="x", expand=False, padx=20, pady=(0, 16))

        footer_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        footer_frame.pack(fill="x", padx=24, pady=(0, 16))

        def refresh_history():
            product_value = product_cb.get()
            product_id = None if product_value in ("", "ALL") else product_value.split(" - ")[0]
            warehouse_id = None if warehouse_cb.get() in ("", "ALL") else warehouse_cb.get()
            start = start_date.get_date()
            end = end_date.get_date()
            history_tree.delete(*history_tree.get_children())
            recent_tree.delete(*recent_tree.get_children())
            try:
                records = self.service.get_transaction_history(start_date=start, end_date=end, product_id=product_id, warehouse_id=warehouse_id)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể tải lịch sử: {e}", parent=dialog)
                return
            for record in records:
                time_str = record["created_at"].strftime("%Y-%m-%d %H:%M") if record["created_at"] else ""
                action = record["operation_type"].capitalize()
                product_label = f"{record['product_id']}" if not self.service.products_map.get(record['product_id']) else f"{record['product_id']} - {self.service.products_map[record['product_id']].name}"
                batch_label = record["batch_id"] or "-"
                quantity = record["quantity"] or 0
                source = f"{record['source_location_type'] or '-'}:{record['source_location_id'] or '-'}"
                target = f"{record['target_location_type'] or '-'}:{record['target_location_id'] or '-'}"
                notes = record.get("notes") or ""
                history_tree.insert("", "end", values=(time_str, action, product_label, batch_label, quantity, source, target, notes))

            recently_viewed = self.service.get_recently_viewed_products()
            if recently_viewed:
                for product in recently_viewed:
                    if product:
                        recent_tree.insert("", "end", values=(product.id, product.name, product.category_id or "N/A", f"${product.price:.2f}" if product.price else "N/A", product.status or "Active"))
            else:
                recent_tree.insert("", "end", values=("-", "Chưa có sản phẩm", "-", "-", "-"))

        ctk.CTkButton(footer_frame, text="Refresh", fg_color=PRIMARY_COLOR, hover_color="#2563eb", font=("Inter", 12, "bold"), command=refresh_history).pack(side="left")
        ctk.CTkButton(footer_frame, text="Clear Filters", fg_color="#6b7280", hover_color="#4b5563", font=("Inter", 12, "bold"), command=lambda: [product_cb.set("ALL"), warehouse_cb.set("ALL"), refresh_history()]).pack(side="left", padx=(10, 0))
        ctk.CTkButton(footer_frame, text="Đóng", fg_color="#6b7280", hover_color="#525252", font=("Inter", 12, "bold"), command=dialog.destroy).pack(side="right")

        refresh_history()

    def open_reports_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Báo cáo kho")
        dialog.geometry("1100x720")
        dialog.attributes("-topmost", True)

        header = ctk.CTkLabel(dialog, text="📈 Báo cáo kho tổng quan", font=("Inter", 20, "bold"), text_color=TEXT_MAIN)
        header.pack(anchor="w", padx=24, pady=(20, 10))

        stats = self.service.get_kpi_stats()
        value_total = self.service.get_inventory_value()
        report_summary = [
            {"title": "Tổng tồn kho", "value": f"{sum(item['total_qty'] for item in self.service.get_current_inventory_report())}", "color": "#2563eb"},
            {"title": "Giá trị kho", "value": f"${value_total:,.2f}", "color": "#0f766e"},
            {"title": "Sản phẩm nhiều hàng tại store", "value": f"{len(self.service.get_products_with_highest_store_inventory(10))}", "color": "#c026d3"},
            {"title": "Hàng tồn lâu", "value": f"{len(self.service.get_aging_inventory(min_days=self.service.settings['aging_days_threshold'], limit=100))}", "color": "#b91c1c"}
        ]

        summary_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        summary_frame.pack(fill="x", padx=24, pady=(0, 20))
        for idx, card in enumerate(report_summary):
            card_frame = ctk.CTkFrame(summary_frame, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color="#e5e7eb")
            card_frame.grid(row=0, column=idx, padx=10, sticky="nsew")
            summary_frame.grid_columnconfigure(idx, weight=1)
            ctk.CTkLabel(card_frame, text=card["title"], font=("Inter", 13, "bold"), text_color=TEXT_SUB).pack(anchor="w", padx=20, pady=(20, 6))
            ctk.CTkLabel(card_frame, text=card["value"], font=("Inter", 26, "bold"), text_color=card["color"]).pack(anchor="w", padx=20, pady=(0, 20))

        content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        # Current inventory by product
        inv_frame = ctk.CTkFrame(content_frame, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color="#e5e7eb")
        inv_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        ctk.CTkLabel(inv_frame, text="Tồn kho hiện tại", font=("Inter", 16, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 10))
        inv_tree = ttk.Treeview(inv_frame, columns=("Product", "Qty", "Value", "Warehouse", "Store"), show="headings", height=9)
        for col in ("Product", "Qty", "Value", "Warehouse", "Store"):
            inv_tree.heading(col, text=col)
            inv_tree.column(col, anchor="center" if col not in ("Product",) else "w", width=120)
        inv_tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        inventory = self.service.get_current_inventory_report()
        for item in inventory[:20]:
            inv_tree.insert("", "end", values=(item["name"], item["total_qty"], f'${item["total_value"]:.2f}', item["warehouse_qty"], item["store_qty"]))

        # Best selling products in stores
        best_frame = ctk.CTkFrame(content_frame, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color="#e5e7eb")
        best_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        ctk.CTkLabel(best_frame, text="Sản phẩm nhiều hàng tại store", font=("Inter", 16, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 10))
        best_tree = ttk.Treeview(best_frame, columns=("Product", "Store Qty", "Warehouse Qty"), show="headings", height=9)
        for col in ("Product", "Store Qty", "Warehouse Qty"):
            best_tree.heading(col, text=col)
            best_tree.column(col, anchor="center" if col != "Product" else "w", width=140)
        best_tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        best_selling = self.service.get_products_with_highest_store_inventory(15)
        for item in best_selling:
            best_tree.insert("", "end", values=(item["name"], item["store_qty"], item["warehouse_qty"]))

        aging_frame = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color="#e5e7eb")
        aging_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        
        # Aging filter controls
        aging_filter_frame = ctk.CTkFrame(aging_frame, fg_color="transparent")
        aging_filter_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(aging_filter_frame, text="📅 Lọc theo ngày nhập:", font=("Inter", 12, "bold")).pack(side="left")
        entry_date_min = DateEntry(aging_filter_frame, width=10, background="#f59e0b", foreground="white", 
                                  borderwidth=0, date_pattern="yyyy-mm-dd")
        entry_date_min.pack(side="left", padx=(10, 2))
        ctk.CTkLabel(aging_filter_frame, text="-", font=("Inter", 12, "bold")).pack(side="left")
        entry_date_max = DateEntry(aging_filter_frame, width=10, background="#f59e0b", foreground="white", 
                                  borderwidth=0, date_pattern="yyyy-mm-dd")
        entry_date_max.pack(side="left", padx=2)
        
        # Location filter for aging
        ctk.CTkLabel(aging_filter_frame, text="Vị trí:", font=("Inter", 12, "bold")).pack(side="left", padx=(20, 5))
        aging_location_var = ctk.StringVar(value="All")
        aging_location_combo = ctk.CTkComboBox(aging_filter_frame, values=["All", "Warehouse", "Store"], 
                                             variable=aging_location_var, width=100)
        aging_location_combo.pack(side="left", padx=2)
        
        def apply_aging_filters():
            try:
                min_date = entry_date_min.get_date() if entry_date_min.get() else None
                max_date = entry_date_max.get_date() if entry_date_max.get() else None
                
                # Get all aging items
                all_aging_items = self.service.get_aging_inventory(min_days=self.service.settings["aging_days_threshold"], limit=1000)
                
                # Apply date filter
                if min_date or max_date:
                    filtered_items = []
                    for item in all_aging_items:
                        if item["entry_date"]:
                            try:
                                entry_date_obj = item["entry_date"] if isinstance(item["entry_date"], date_type) else datetime.strptime(str(item["entry_date"]), "%Y-%m-%d").date()
                                if min_date and entry_date_obj < min_date:
                                    continue
                                if max_date and entry_date_obj > max_date:
                                    continue
                            except:
                                continue
                        filtered_items.append(item)
                    display_items = filtered_items[:25]
                else:
                    display_items = all_aging_items[:25]
                
                # Apply location filter
                loc_filter = aging_location_var.get()
                if loc_filter == "Warehouse":
                    display_items = [item for item in display_items if "🏢" in item["location"]]
                elif loc_filter == "Store":
                    display_items = [item for item in display_items if "🏪" in item["location"]]
                
                # Update treeview
                aging_tree.delete(*aging_tree.get_children())
                for item in display_items:
                    aging_tree.insert("", "end", values=(item["batch_id"], item["name"], item["location"], item["quantity"], item["entry_date"], item["days_in_stock"]))
                    
            except Exception as e:
                print(f"Error applying aging filters: {e}")
        
        ctk.CTkButton(aging_filter_frame, text="🔄 Lọc", fg_color="#f59e0b", hover_color="#d97706",
                      font=("Inter", 11, "bold"), height=28, command=apply_aging_filters).pack(side="right", padx=(10, 0))
        
        ctk.CTkLabel(aging_frame, text="Hàng tồn lâu", font=("Inter", 16, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(10, 10))
        aging_tree = ttk.Treeview(aging_frame, columns=("Batch", "Product", "Location", "Qty", "Entry Date", "Days"), show="headings", height=10)
        for col in ("Batch", "Product", "Location", "Qty", "Entry Date", "Days"):
            aging_tree.heading(col, text=col)
            aging_tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=120)
        aging_tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        aging_items = self.service.get_aging_inventory(min_days=self.service.settings["aging_days_threshold"], limit=25)
        for item in aging_items:
            aging_tree.insert("", "end", values=(item["batch_id"], item["name"], item["location"], item["quantity"], item["entry_date"], item["days_in_stock"]))

        ctk.CTkButton(dialog, text="Đóng", fg_color="#6b7280", hover_color="#525252", command=dialog.destroy).pack(pady=16)

    def open_warning_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Batch Alerts")
        dialog.geometry("940x560")
        dialog.attributes("-topmost", True)

        header = ctk.CTkLabel(dialog, text="Batch Alerts", font=("Inter", 20, "bold"), text_color=TEXT_MAIN)
        header.pack(anchor="w", padx=24, pady=(20, 10))

        desc = ctk.CTkLabel(dialog, text="Danh sách hàng sắp hết hạn và hàng tồn kho thấp", font=("Inter", 13, "bold"), text_color=TEXT_SUB)
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
        
        # Expiring items filter controls
        exp_filter_frame = ctk.CTkFrame(exp_frame, fg_color="transparent")
        exp_filter_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(exp_filter_frame, text="📅 Ngày HH:", font=("Inter", 11, "bold")).pack(side="left")
        exp_filter_min = DateEntry(exp_filter_frame, width=10, background="#dc2626", foreground="white", 
                                  borderwidth=0, date_pattern="yyyy-mm-dd")
        exp_filter_min.pack(side="left", padx=(5, 2))
        ctk.CTkLabel(exp_filter_frame, text="-", font=("Inter", 11, "bold")).pack(side="left")
        exp_filter_max = DateEntry(exp_filter_frame, width=10, background="#dc2626", foreground="white", 
                                  borderwidth=0, date_pattern="yyyy-mm-dd")
        exp_filter_max.pack(side="left", padx=2)
        
        # Location filter for expiring items
        ctk.CTkLabel(exp_filter_frame, text="Vị trí:", font=("Inter", 11, "bold")).pack(side="left", padx=(20, 5))
        exp_location_var = ctk.StringVar(value="All")
        exp_location_combo = ctk.CTkComboBox(exp_filter_frame, values=["All", "Warehouse", "Store"], 
                                           variable=exp_location_var, width=90)
        exp_location_combo.pack(side="left", padx=2)
        
        def apply_exp_filters():
            try:
                min_date = exp_filter_min.get_date() if exp_filter_min.get() else None
                max_date = exp_filter_max.get_date() if exp_filter_max.get() else None
                
                # Get all expiring items
                all_exp_items = self.service.get_expiring_items()
                
                # Apply date filter
                if min_date or max_date:
                    filtered_items = []
                    for inv in all_exp_items:
                        exp_date = inv.exp_date
                        if isinstance(exp_date, str):
                            try:
                                exp_date_obj = datetime.strptime(exp_date, "%Y-%m-%d").date()
                            except:
                                continue
                        elif isinstance(exp_date, date_type):
                            exp_date_obj = exp_date
                        else:
                            continue
                            
                        if min_date and exp_date_obj < min_date:
                            continue
                        if max_date and exp_date_obj > max_date:
                            continue
                        filtered_items.append(inv)
                    display_items = filtered_items
                else:
                    display_items = all_exp_items
                
                # Apply location filter
                loc_filter = exp_location_var.get()
                if loc_filter == "Warehouse":
                    display_items = [inv for inv in display_items if inv.warehouse_id and not inv.store_id]
                elif loc_filter == "Store":
                    display_items = [inv for inv in display_items if inv.store_id]
                
                # Update treeview
                exp_tree.delete(*exp_tree.get_children())
                today = datetime.today().date()
                for inv in display_items:
                    prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
                    loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
                    exp_date = inv.exp_date
                    if isinstance(exp_date, str):
                        exp_date_obj = datetime.strptime(exp_date, "%Y-%m-%d").date()
                    else:
                        exp_date_obj = exp_date
                    
                    remaining_days = (exp_date_obj - today).days
                    if remaining_days < 0:
                        status_tag = "expired"
                        remaining_text = f"Quá hạn {-remaining_days} ngày"
                    elif remaining_days <= 7:
                        status_tag = "expiring"
                        remaining_text = f"{remaining_days} ngày"
                    else:
                        status_tag = "warning"
                        remaining_text = f"{remaining_days} ngày"
                    
                    exp_tree.insert("", "end", values=(prod_name, inv.batch_id, loc, inv.quantity, exp_date, remaining_text), tags=(status_tag,))
                
                # Update count
                count_label.configure(text=f"⏳ Expiring Soon ({len(display_items)})")
                    
            except Exception as e:
                print(f"Error applying exp filters: {e}")
        
        ctk.CTkButton(exp_filter_frame, text="🔄 Lọc", fg_color="#dc2626", hover_color="#b91c1c",
                      font=("Inter", 10, "bold"), height=26, command=apply_exp_filters).pack(side="right", padx=(5, 0))
        
        count_label = ctk.CTkLabel(exp_frame, text=f"⏳ Expiring Soon ({len(exp_items)})", font=("Inter", 16, "bold"), text_color="#b91c1c")
        count_label.pack(anchor="w", padx=20, pady=(5, 10))
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
                exp_date_obj = datetime.strptime(exp_date, "%Y-%m-%d").date()
            else:
                exp_date_obj = exp_date
            
            remaining_days = (exp_date_obj - today).days
            if remaining_days < 0:
                status_tag = "expired"
                remaining_text = f"Quá hạn {-remaining_days} ngày"
            elif remaining_days <= 7:
                status_tag = "expiring"
                remaining_text = f"{remaining_days} ngày"
            else:
                status_tag = "warning"
                remaining_text = f"{remaining_days} ngày"
            
            exp_tree.insert("", "end", values=(prod_name, inv.batch_id, loc, inv.quantity, exp_date, remaining_text), tags=(status_tag,))

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
            ctk.CTkButton(button_frame, text="🔁 Create Transfer", fg_color="#8b5cf6", hover_color="#7c3aed",
                          font=("Inter", 13, "bold"), height=38,
                          command=self.open_transfer_dialog).pack(side="left", padx=5)
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
                heading_text = col.upper() if col in ("ID", "Name") else f"{col.upper()} ▼"
                self.tree.heading(col, text=heading_text)
            self.tree.bind("<Double-1>", self.on_product_double_click)
            self.tree.bind("<Button-1>", self.on_product_tree_click)
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
            # Ghi lịch xem sản phẩm
            self.service.find_product_by_id(str(prod_id))
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

    def _init_product_column_filters(self):
        if self.product_column_filters is None:
            self.product_column_filters = {
                "ID": {"type": "text", "value": ""},
                "Name": {"type": "text", "value": ""},
                "Category ID": {"type": "text", "value": ""},
                "Price": {"type": "number", "min": None, "max": None},
                "Status": {"type": "choice", "value": "All", "choices": ["All", "Active", "Inactive"]}
            }

    def _open_product_column_filter(self, col_name):
        self._init_product_column_filters()
        popup = ctk.CTkToplevel(self)
        popup.title(f"Lọc {col_name}")
        popup.geometry("360x220")
        popup.attributes("-topmost", True)
        popup.transient(self)
        popup.grab_set()
        popup.focus_force()
        popup.resizable(False, False)

        ctk.CTkLabel(popup, text=f"Lọc theo {col_name}", font=("Inter", 14, "bold")).pack(pady=(18, 10))
        body = ctk.CTkFrame(popup, fg_color="transparent")
        body.pack(padx=20, pady=10, fill="x")

        def save_and_close():
            self.refresh_table()
            popup.destroy()

        filter_def = self.product_column_filters[col_name]
        if filter_def["type"] == "text":
            entry = ctk.CTkEntry(body, width=320, placeholder_text="Nhập nội dung lọc...")
            entry.pack(pady=8)
            entry.insert(0, filter_def["value"])

            def save_text():
                filter_def["value"] = entry.get().strip()
                save_and_close()
            save_fn = save_text

        elif filter_def["type"] == "number":
            min_ent = ctk.CTkEntry(body, width=140, placeholder_text="Min")
            max_ent = ctk.CTkEntry(body, width=140, placeholder_text="Max")
            min_ent.pack(side="left", padx=(0, 5))
            max_ent.pack(side="left", padx=(5, 0))
            if filter_def["min"] is not None:
                min_ent.insert(0, str(filter_def["min"]))
            if filter_def["max"] is not None:
                max_ent.insert(0, str(filter_def["max"]))

            def save_number():
                try:
                    filter_def["min"] = float(min_ent.get()) if min_ent.get().strip() else None
                    filter_def["max"] = float(max_ent.get()) if max_ent.get().strip() else None
                except ValueError:
                    filter_def["min"] = None
                    filter_def["max"] = None
                save_and_close()
            save_fn = save_number

        else:
            combo = ctk.CTkComboBox(body, values=filter_def["choices"], width=320)
            combo.set(filter_def["value"])
            combo.pack(pady=8)

            def save_choice():
                filter_def["value"] = combo.get()
                save_and_close()
            save_fn = save_choice

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Áp dụng", fg_color=PRIMARY_COLOR, width=120, command=save_fn).pack(side="left", padx=8)

        def clear_filter():
            if filter_def["type"] == "text":
                filter_def["value"] = ""
            elif filter_def["type"] == "number":
                filter_def["min"] = None
                filter_def["max"] = None
            else:
                filter_def["value"] = "All"
            save_and_close()

        ctk.CTkButton(btn_frame, text="Xoá lọc", fg_color="#fee2e2", text_color="#b91c1c", hover_color="#fca5a5", width=120, command=clear_filter).pack(side="left", padx=8)

    def on_product_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            col = self.tree.identify_column(event.x)
            if col == "#1":
                return
            idx = int(col.replace("#", "")) - 1
            cols = ("✓", "ID", "Name", "Category ID", "Price", "Status")
            if idx in (1, 2):
                return
            if idx >= 0 and idx < len(cols):
                self._open_product_column_filter(cols[idx])
                return "break"
            return
        self.on_tree_click_product_checkbox(event)

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
                        font=("Inter", 12, "bold")).pack(pady=20)
            return
        
        # Treeview để hiển thị batch
        cols = ("Batch ID", "Product", "MFG Date", "Quantity", "Unit Price", "Location", "Exp Date", "Entry Date", "Status")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=20)
        for col in cols:
            tree.heading(col, text=f"{col.upper()} ▼")
            tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=100)
        
        tree.tag_configure("instock", foreground="#0f766e", background="#ecfdf5")
        tree.tag_configure("lowstock", foreground="#78350f", background="#fef3c7")
        tree.tag_configure("expired", foreground="#7f1d1d", background="#fee2e2")
        tree.tag_configure("expiring", foreground="#9a3412", background="#ffedd5")
        tree.tag_configure("warning", foreground="#92400e", background="#fef9c3")

        original_batch_items = list(batch_items)
        column_filters = {
            "Batch ID": {"type": "text", "value": ""},
            "Product": {"type": "text", "value": ""},
            "MFG Date": {"type": "date", "min": None, "max": None},
            "Quantity": {"type": "number", "min": None, "max": None},
            "Unit Price": {"type": "number", "min": None, "max": None},
            "Location": {"type": "choice", "value": "All", "choices": ["All", "Warehouse", "Store"]},
            "Exp Date": {"type": "date", "min": None, "max": None},
            "Entry Date": {"type": "date", "min": None, "max": None},
            "Status": {"type": "choice", "value": "All", "choices": ["All", "In Stock", "Low Stock", "Expiring", "Warning", "Expired"]}
        }

        def parse_date_value(value):
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except Exception:
                    return None
            return value

        def batch_matches_filter(inv):
            # Batch ID / Product text filters
            if column_filters["Batch ID"]["value"]:
                if column_filters["Batch ID"]["value"].lower() not in str(inv.batch_id).lower():
                    return False
            if column_filters["Product"]["value"]:
                prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', '')
                if column_filters["Product"]["value"].lower() not in prod_name.lower():
                    return False

            # Quantity filter
            if column_filters["Quantity"]["min"] is not None and inv.quantity < column_filters["Quantity"]["min"]:
                return False
            if column_filters["Quantity"]["max"] is not None and inv.quantity > column_filters["Quantity"]["max"]:
                return False

            # Unit Price filter
            if column_filters["Unit Price"]["min"] is not None and inv.unit_price < column_filters["Unit Price"]["min"]:
                return False
            if column_filters["Unit Price"]["max"] is not None and inv.unit_price > column_filters["Unit Price"]["max"]:
                return False

            # Date filters
            for date_col in ["MFG Date", "Exp Date", "Entry Date"]:
                date_value = getattr(inv, date_col.lower().replace(" ", "_"), None)
                date_obj = parse_date_value(date_value)
                min_date = column_filters[date_col]["min"]
                max_date = column_filters[date_col]["max"]
                if min_date and date_obj is not None and date_obj < min_date:
                    return False
                if max_date and date_obj is not None and date_obj > max_date:
                    return False

            # Location filter
            loc_filter = column_filters["Location"]["value"]
            if loc_filter == "Warehouse" and not (inv.warehouse_id and not inv.store_id):
                return False
            if loc_filter == "Store" and not inv.store_id:
                return False

            # Status filter
            status_filter = column_filters["Status"]["value"]
            if status_filter != "All":
                status_text, _ = self._format_batch_status_and_tag(inv, self.service.settings.get("low_stock_threshold", 10))
                if status_filter.lower() not in status_text.lower():
                    return False

            return True

        def refresh_tree(filtered_items):
            tree.delete(*tree.get_children())
            low_stock_threshold = self.service.settings.get("low_stock_threshold", 10)
            for inv in filtered_items:
                prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
                status_text, status_tag = self._format_batch_status_and_tag(inv, low_stock_threshold)
                loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
                tree.insert("", "end", values=(inv.batch_id, prod_name, inv.mfg_date, inv.quantity, inv.unit_price, loc, inv.exp_date, inv.entry_date, status_text), tags=(status_tag,))

        def apply_current_filters():
            filtered = [inv for inv in original_batch_items if batch_matches_filter(inv)]
            refresh_tree(filtered)

        def open_column_filter(col_name):
            popup = ctk.CTkToplevel(self)
            popup.title(f"Lọc {col_name}")
            popup.geometry("380x220")
            popup.attributes("-topmost", True)
            popup.transient(self)
            popup.grab_set()
            popup.focus_force()
            popup.resizable(False, False)

            ctk.CTkLabel(popup, text=f"Lọc theo {col_name}", font=("Inter", 14, "bold")).pack(pady=(18, 10))
            body = ctk.CTkFrame(popup, fg_color="transparent")
            body.pack(padx=20, pady=10, fill="x")

            if column_filters[col_name]["type"] == "text":
                entry = ctk.CTkEntry(body, width=320, placeholder_text="Nhập ký tự tìm kiếm...")
                entry.pack(pady=8)
                entry.insert(0, column_filters[col_name]["value"])

                def save():
                    column_filters[col_name]["value"] = entry.get().strip()
                    apply_current_filters()
                    popup.destroy()

            elif column_filters[col_name]["type"] == "number":
                min_ent = ctk.CTkEntry(body, width=140, placeholder_text="Min")
                max_ent = ctk.CTkEntry(body, width=140, placeholder_text="Max")
                min_ent.pack(side="left", padx=(0, 5))
                max_ent.pack(side="left", padx=(5, 0))
                if column_filters[col_name]["min"] is not None:
                    min_ent.insert(0, str(column_filters[col_name]["min"]))
                if column_filters[col_name]["max"] is not None:
                    max_ent.insert(0, str(column_filters[col_name]["max"]))

                def save():
                    try:
                        column_filters[col_name]["min"] = float(min_ent.get()) if min_ent.get().strip() else None
                        column_filters[col_name]["max"] = float(max_ent.get()) if max_ent.get().strip() else None
                    except ValueError:
                        column_filters[col_name]["min"] = None
                        column_filters[col_name]["max"] = None
                    apply_current_filters()
                    popup.destroy()

            elif column_filters[col_name]["type"] == "date":
                min_picker = DateEntry(body, width=14, background=PRIMARY_COLOR, foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
                max_picker = DateEntry(body, width=14, background=PRIMARY_COLOR, foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
                min_picker.pack(side="left", padx=(0, 5))
                max_picker.pack(side="left", padx=(5, 0))
                if column_filters[col_name]["min"]:
                    min_picker.set_date(column_filters[col_name]["min"])
                if column_filters[col_name]["max"]:
                    max_picker.set_date(column_filters[col_name]["max"])

                def save():
                    column_filters[col_name]["min"] = min_picker.get_date() if min_picker.get() else None
                    column_filters[col_name]["max"] = max_picker.get_date() if max_picker.get() else None
                    apply_current_filters()
                    popup.destroy()

            elif column_filters[col_name]["type"] == "choice":
                combo = ctk.CTkComboBox(body, values=column_filters[col_name]["choices"], width=320)
                combo.set(column_filters[col_name]["value"])
                combo.pack(pady=8)

                def save():
                    column_filters[col_name]["value"] = combo.get()
                    apply_current_filters()
                    popup.destroy()

            btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
            btn_frame.pack(pady=12)
            ctk.CTkButton(btn_frame, text="Áp dụng", fg_color=PRIMARY_COLOR, width=120, command=save).pack(side="left", padx=8)
            ctk.CTkButton(btn_frame, text="Xoá lọc", fg_color="#fee2e2", text_color="#b91c1c", hover_color="#fca5a5", width=120,
                          command=lambda: [
                              column_filters[col_name].update({"value": ""} if column_filters[col_name]["type"] == "text" else {"min": None, "max": None} if column_filters[col_name]["type"] in ["number", "date"] else {"value": "All"}),
                              apply_current_filters(),
                              popup.destroy()
                          ]).pack(side="left", padx=8)

        def on_header_click(event):
            if tree.identify_region(event.x, event.y) != "heading":
                return
            col = tree.identify_column(event.x)
            try:
                idx = int(col.replace("#", "")) - 1
                if idx in (0, 1):
                    return
                open_column_filter(cols[idx])
                return "break"
            except Exception:
                return

        tree.bind("<Button-1>", on_header_click)
        refresh_tree(original_batch_items)
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
            # Apply category filter if set
            if self.filter_category_id:
                data = [p for p in data if str(p.category_id) == self.filter_category_id]
            
            # Apply header filters if any
            if self.product_column_filters:
                header_filtered = []
                for p in data:
                    if self.product_column_filters["ID"]["value"] and self.product_column_filters["ID"]["value"].lower() not in str(p.id).lower():
                        continue
                    if self.product_column_filters["Name"]["value"] and self.product_column_filters["Name"]["value"].lower() not in str(p.name).lower():
                        continue
                    if self.product_column_filters["Category ID"]["value"] and self.product_column_filters["Category ID"]["value"].lower() not in str(p.category_id).lower():
                        continue
                    if self.product_column_filters["Price"]["min"] is not None and (p.price is None or p.price < self.product_column_filters["Price"]["min"]):
                        continue
                    if self.product_column_filters["Price"]["max"] is not None and (p.price is None or p.price > self.product_column_filters["Price"]["max"]):
                        continue
                    if self.product_column_filters["Status"]["value"] != "All":
                        product_status = getattr(p, 'status', 'Active') or 'Active'
                        if self.product_column_filters["Status"]["value"].lower() not in product_status.lower():
                            continue
                    header_filtered.append(p)
                data = header_filtered
            
            # Display filtered data
            for p in data:
                checkbox = "✓" if str(p.id) in self.selected_products else "☐"
                price = f"${p.price:.2f}" if p.price else "N/A"
                status = getattr(p, 'status', 'Active') or 'Active'
                self.tree.insert("", "end", values=(checkbox, p.id, p.name, p.category_id, price, status))
                
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

    def apply_product_filters(self):
        """Apply filters for Product tab"""
        self.refresh_table()

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
        ctk.CTkLabel(row, text="Từ:", font=("Inter", 12, "bold")).pack(side="left", padx=(0, 6))
        min_ent = ctk.CTkEntry(row, width=90, placeholder_text="0")
        min_ent.pack(side="left", padx=(0, 16))
        if self.range_filter["qty_min"] is not None:
            min_ent.insert(0, str(self.range_filter["qty_min"]))

        ctk.CTkLabel(row, text="Đến:", font=("Inter", 12, "bold")).pack(side="left", padx=(0, 6))
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
        ctk.CTkLabel(row, text="Từ:", font=("Inter", 12, "bold")).pack(side="left", padx=(0, 6))
        from_picker = DateEntry(row, width=12, background=PRIMARY_COLOR,
                                foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
        from_picker.pack(side="left", padx=(0, 20))
        if self.range_filter["exp_from"]:
            from_picker.set_date(self.range_filter["exp_from"])

        ctk.CTkLabel(row, text="Đến:", font=("Inter", 12, "bold")).pack(side="left", padx=(0, 6))
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
        if self.active_tab != "Product":
            messagebox.showwarning("Warning", "Vui lòng mở tab Product và chọn một sản phẩm để tạo task chuyển hàng!")
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Vui lòng chọn 1 sản phẩm để tạo task chuyển hàng!")
            return

        item_data = self.tree.item(selected[0])['values']
        if len(item_data) < 2:
            messagebox.showwarning("Warning", "Dữ liệu chọn không hợp lệ. Vui lòng chọn một sản phẩm.")
            return

        product_id = item_data[1]  # ID nằm ở cột thứ 2 trong Product tab

        dialog = ctk.CTkToplevel(self)
        dialog.title("Create Transfer Task")
        dialog.geometry("500x350")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text=f"Transfer Task: {product_id}", font=("Inter", 14, "bold")).pack(pady=(20, 10))

        # Quantity input
        qty_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        qty_frame.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkLabel(qty_frame, text="Quantity to Transfer:", font=("Inter", 12, "bold")).pack(anchor="w")
        qty_ent = ctk.CTkEntry(qty_frame, width=400, placeholder_text="Nhập số lượng cần chuyển")
        qty_ent.pack(pady=(5, 0))

        # Transfer mode selection
        mode_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        mode_frame.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkLabel(mode_frame, text="Transfer Type:", font=("Inter", 12, "bold")).pack(anchor="w")
        type_cb = ctk.CTkComboBox(mode_frame, values=["Warehouse → Warehouse", "Store → Store", "Warehouse → Store", "Store → Warehouse"], width=400,
                                   command=lambda val: refresh_locations())
        type_cb.pack(pady=(5, 0))
        type_cb.set("Warehouse → Store")

        # Source Location selection
        source_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        source_frame.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkLabel(source_frame, text="Source Location:", font=("Inter", 12, "bold")).pack(anchor="w")
        source_cb = ctk.CTkComboBox(source_frame, values=[], width=400,
                                    command=lambda val: update_target_locations())
        source_cb.pack(pady=(5, 0))

        # Target Location selection
        target_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        target_frame.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkLabel(target_frame, text="Target Location:", font=("Inter", 12, "bold")).pack(anchor="w")
        target_cb = ctk.CTkComboBox(target_frame, values=[], width=400,
                                    command=lambda val: show_suggestion())
        target_cb.pack(pady=(5, 0))

        suggestions_data = []

        def parse_transfer_type(transfer_type_label):
            if transfer_type_label == "Warehouse → Warehouse":
                return "warehouse", "warehouse"
            if transfer_type_label == "Store → Store":
                return "store", "store"
            if transfer_type_label == "Warehouse → Store":
                return "warehouse", "store"
            if transfer_type_label == "Store → Warehouse":
                return "store", "warehouse"
            return "warehouse", "store"

        def update_target_locations():
            source_type, target_type = parse_transfer_type(type_cb.get())
            source_location = source_cb.get()
            if target_type == "warehouse":
                target_ids = list(self.service.warehouses_map.keys())
            else:
                target_ids = list(self.service.stores_map.keys())

            if source_type == target_type and source_location and source_location != "All":
                target_ids = [tid for tid in target_ids if tid != source_location]

            target_cb.configure(values=target_ids)
            if target_ids:
                target_cb.set(target_ids[0])

        def refresh_locations():
            source_type, target_type = parse_transfer_type(type_cb.get())
            source_ids = self.service.get_product_location_ids(product_id, source_type)
            if not source_ids:
                source_cb.configure(values=["All"])
                source_cb.set("All")
                target_cb.configure(values=[])
                suggestion_label.configure(text=f"Không tìm thấy nguồn {source_type} có sản phẩm {product_id}")
                suggestions_data.clear()
                return

            source_ids = ["All"] + source_ids
            source_cb.configure(values=source_ids)
            source_cb.set("All")
            update_target_locations()

        # CTkComboBox uses command callback, not Tk virtual event binding.

        # Suggestion frame
        suggestion_frame = ctk.CTkFrame(dialog, fg_color="#f0fdf4", corner_radius=8, border_width=1, border_color="#86efac")
        suggestion_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        suggestion_label = ctk.CTkLabel(suggestion_frame, text="Gợi ý kết hợp batch sẽ hiển thị ở đây", 
                                       font=("Inter", 11, "bold"), text_color="#166534", wraplength=440, justify="left")
        suggestion_label.pack(padx=15, pady=(15, 0), anchor="w")

        options_container = ctk.CTkFrame(suggestion_frame, fg_color="transparent")
        options_container.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        def format_combo_text(combo):
            lines = []
            if combo['option_type'] == 'full':
                batch = combo['batches'][0]
                lines.append(f"Nên lấy full batch {batch['batch_id']} ({batch['batch_qty']})")
            elif combo['option_type'] == 'split':
                batch = combo['batches'][0]
                remaining_qty = batch['batch_qty'] - batch['take_qty']
                lines.append(
                    f"Split batch {batch['batch_id']} ({batch['batch_qty']}) thành batch {batch['batch_id']} ({batch['take_qty']}) [transfer] "
                    f"và batch {batch['batch_id']} ({remaining_qty})"
                )
            else:
                parts = []
                for batch in combo['batches']:
                    if batch['take_qty'] == batch['batch_qty']:
                        parts.append(f"full batch {batch['batch_id']} ({batch['batch_qty']})")
                    else:
                        remain_qty = batch['batch_qty'] - batch['take_qty']
                        parts.append(
                            f"split batch {batch['batch_id']} ({batch['batch_qty']}) thành batch {batch['batch_id']} ({batch['take_qty']}) [transfer] "
                            f"và batch {batch['batch_id']} ({remain_qty})"
                        )
                lines.append("Nên lấy " + " và ".join(parts))
            return "\n".join(lines)

        def create_task_for_option(idx):
            if not suggestions_data or idx < 0 or idx >= len(suggestions_data):
                messagebox.showerror("Lỗi", "Option không hợp lệ", parent=dialog)
                return
            target_location = target_cb.get()
            location_type = type_cb.get()
            if not target_location:
                messagebox.showerror("Lỗi", "Vui lòng chọn đích chuyển hàng!", parent=dialog)
                return
            best_combo = suggestions_data[idx]
            try:
                task_ids = []
                source_type, target_type = parse_transfer_type(type_cb.get())
                for batch_info in best_combo['batches']:
                    task = self.service.create_transfer_task(
                        product_id, target_location, target_type, batch_info['take_qty'], 
                        priority="normal", strategy="fefo",
                        source_batch_id=batch_info['batch_id']
                    )
                    task_ids.append(task.task_id)

                dialog.destroy()
                msg = f"✅ Đã tạo task(s) chuyển hàng:\n"
                if best_combo['option_type'] == 'full':
                    batch = best_combo['batches'][0]
                    msg += f"Task {task_ids[0]}: full batch {batch['batch_id']} ({batch['take_qty']})"
                else:
                    msg += f"Tasks: {', '.join(task_ids)}\n"
                    for batch_info in best_combo['batches']:
                        msg += f"  - {batch_info['batch_id']}: {batch_info['take_qty']} sản phẩm\n"
                messagebox.showinfo("Success", msg)
                self.open_task_manager_dialog()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi tạo task: {e}", parent=dialog)

        def render_suggestions():
            for child in options_container.winfo_children():
                child.destroy()

            if not suggestions_data:
                return

            for idx, combo in enumerate(suggestions_data):
                option_frame = ctk.CTkFrame(options_container, fg_color="white",
                                            corner_radius=10, border_width=1,
                                            border_color="#d1fae5")
                option_frame.pack(fill="x", padx=10, pady=6)

                text = f"Option {idx + 1}:\n{format_combo_text(combo)}"
                ctk.CTkLabel(option_frame, text=text, font=("Inter", 11, "bold"),
                             text_color="#0f766e", wraplength=360,
                             justify="left").pack(side="left", fill="both", expand=True, padx=(12, 8), pady=12)

                btn = ctk.CTkButton(option_frame, text="Tạo task", width=90,
                                    fg_color="#10b981", hover_color="#059669",
                                    font=("Inter", 11, "bold"),
                                    command=lambda i=idx: create_task_for_option(i))
                btn.pack(side="right", padx=10, pady=10)

        def show_suggestion():
            qty_str = qty_ent.get().strip()
            if not qty_str or not qty_str.isdigit():
                suggestion_label.configure(text="⚠️ Vui lòng nhập số lượng hợp lệ (số nguyên > 0)")
                suggestions_data.clear()
                render_suggestions()
                return
            
            transfer_qty = int(qty_str)
            if transfer_qty <= 0:
                suggestion_label.configure(text="⚠️ Số lượng phải > 0")
                suggestions_data.clear()
                render_suggestions()
                return

            source_location = source_cb.get()
            source_type, target_type = parse_transfer_type(type_cb.get())
            if not source_location:
                suggestion_label.configure(text="⚠️ Vui lòng chọn nguồn chuyển hàng")
                suggestions_data.clear()
                render_suggestions()
                return
            
            try:
                source_id = source_location if source_location != "All" else "All"
                suggestions_data[:] = self.service.suggest_batch_combinations(product_id, transfer_qty, source_location_type=source_type, source_location_id=source_id, sort_strategy="fefo")
                if not suggestions_data:
                    suggestion_label.configure(text="❌ Không có batch nào ở nguồn hoặc không đủ số lượng")
                    render_suggestions()
                    return
                
                suggestion_label.configure(text="Chọn option phù hợp để tạo task chuyển hàng:")
                render_suggestions()
            except Exception as e:
                suggestion_label.configure(text=f"❌ Lỗi: {e}")
                suggestions_data.clear()
                render_suggestions()

        qty_ent.bind("<KeyRelease>", lambda e: show_suggestion())
        target_cb.bind("<<ComboboxSelected>>", lambda e: show_suggestion())

        refresh_locations()

        qty_ent.bind("<KeyRelease>", lambda e: show_suggestion())

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(btn_frame, text="Refresh", fg_color="#6b7280", hover_color="#4b5563",
                      font=("Inter", 12, "bold"), command=show_suggestion).pack(side="right", padx=5)

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
                        font=("Inter", 12, "bold")).pack(pady=20)
            return
        
        # Treeview để hiển thị batch
        cols = ("Batch ID", "Product", "MFG Date", "Quantity", "Unit Price", "Location", "Exp Date", "Entry Date", "Status")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=20)
        for col in cols:
            heading_text = col.upper() if col in ("Batch ID", "Product") else f"{col.upper()} ▼"
            tree.heading(col, text=heading_text)
            tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=100)
        tree.tag_configure("instock", foreground="#0f766e", background="#ecfdf5")
        tree.tag_configure("lowstock", foreground="#78350f", background="#fef3c7")
        tree.tag_configure("expired", foreground="#7f1d1d", background="#fee2e2")
        tree.tag_configure("expiring", foreground="#9a3412", background="#ffedd5")
        tree.tag_configure("warning", foreground="#92400e", background="#fef9c3")
        for inv in all_batch:
            prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
            status_text, status_tag = self._format_batch_status_and_tag(inv, low_stock_threshold)
            loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
            tree.insert("", "end", values=(inv.batch_id, prod_name, inv.mfg_date, inv.quantity, inv.unit_price, loc, inv.exp_date, inv.entry_date, status_text), tags=(status_tag,))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)

    def open_batch_dialog_for_products(self):
        """Hiển thị hộp thoại batch của các product được chọn"""
        if not self.selected_products:
            messagebox.showwarning("Warning", "Vui lòng chọn ít nhất một product (checkbox ✓)", parent=self)
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Batch by Product")
        dialog.geometry("1100x600")
        dialog.attributes("-topmost", True)
        
        # Tổng hợp batch của các product được chọn
        all_batch = []
        for prod_id in self.selected_products:
            batch_items = self.service.load_product_batch(prod_id)
            all_batch.extend(batch_items if batch_items else [])
        
        if not all_batch:
            ctk.CTkLabel(dialog, text="No batch found for selected products", 
                        font=("Inter", 12, "bold")).pack(pady=20)
            return
        
        # Treeview để hiển thị batch
        cols = ("Batch ID", "Product", "MFG Date", "Quantity", "Unit Price", "Location", "Exp Date", "Entry Date", "Status")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=20)
        for col in cols:
            heading_text = col.upper() if col in ("Batch ID", "Product") else f"{col.upper()} ▼"
            tree.heading(col, text=heading_text)
            tree.column(col, anchor="center" if col not in ("Product", "Location") else "w", width=100)
        tree.tag_configure("instock", foreground="#0f766e", background="#ecfdf5")
        tree.tag_configure("lowstock", foreground="#78350f", background="#fef3c7")
        tree.tag_configure("expired", foreground="#7f1d1d", background="#fee2e2")
        tree.tag_configure("expiring", foreground="#9a3412", background="#ffedd5")
        tree.tag_configure("warning", foreground="#92400e", background="#fef9c3")

        original_all_batch = list(all_batch)
        column_filters = {
            "Batch ID": {"type": "text", "value": ""},
            "Product": {"type": "text", "value": ""},
            "MFG Date": {"type": "date", "min": None, "max": None},
            "Quantity": {"type": "number", "min": None, "max": None},
            "Unit Price": {"type": "number", "min": None, "max": None},
            "Location": {"type": "choice", "value": "All", "choices": ["All", "Warehouse", "Store"]},
            "Exp Date": {"type": "date", "min": None, "max": None},
            "Entry Date": {"type": "date", "min": None, "max": None},
            "Status": {"type": "choice", "value": "All", "choices": ["All", "In Stock", "Low Stock", "Expiring", "Warning", "Expired"]}
        }

        def parse_date_value(value):
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except Exception:
                    return None
            return value

        def batch_matches_filter(inv):
            if column_filters["Batch ID"]["value"] and column_filters["Batch ID"]["value"].lower() not in str(inv.batch_id).lower():
                return False
            if column_filters["Product"]["value"]:
                prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', '')
                if column_filters["Product"]["value"].lower() not in prod_name.lower():
                    return False
            if column_filters["Quantity"]["min"] is not None and inv.quantity < column_filters["Quantity"]["min"]:
                return False
            if column_filters["Quantity"]["max"] is not None and inv.quantity > column_filters["Quantity"]["max"]:
                return False
            if column_filters["Unit Price"]["min"] is not None and inv.unit_price < column_filters["Unit Price"]["min"]:
                return False
            if column_filters["Unit Price"]["max"] is not None and inv.unit_price > column_filters["Unit Price"]["max"]:
                return False
            for date_col in ["MFG Date", "Exp Date", "Entry Date"]:
                value = getattr(inv, date_col.lower().replace(" ", "_"), None)
                date_obj = parse_date_value(value)
                if column_filters[date_col]["min"] and date_obj is not None and date_obj < column_filters[date_col]["min"]:
                    return False
                if column_filters[date_col]["max"] and date_obj is not None and date_obj > column_filters[date_col]["max"]:
                    return False
            loc_filter = column_filters["Location"]["value"]
            if loc_filter == "Warehouse" and not (inv.warehouse_id and not inv.store_id):
                return False
            if loc_filter == "Store" and not inv.store_id:
                return False
            status_filter = column_filters["Status"]["value"]
            if status_filter != "All":
                status_text, _ = self._format_batch_status_and_tag(inv, self.service.settings.get("low_stock_threshold", 10))
                if status_filter.lower() not in status_text.lower():
                    return False
            return True

        def refresh_tree(filtered_items):
            tree.delete(*tree.get_children())
            low_stock_threshold = self.service.settings.get("low_stock_threshold", 10)
            for inv in filtered_items:
                prod_name = getattr(self.service.products_map.get(inv.product_id), 'name', inv.product_id)
                status_text, status_tag = self._format_batch_status_and_tag(inv, low_stock_threshold)
                loc = f"🏪 {inv.store_id}" if inv.store_id else f"🏢 {inv.warehouse_id}"
                tree.insert("", "end", values=(inv.batch_id, prod_name, inv.mfg_date, inv.quantity, inv.unit_price, loc, inv.exp_date, inv.entry_date, status_text), tags=(status_tag,))

        def open_column_filter(col_name):
            popup = ctk.CTkToplevel(dialog)
            popup.title(f"Lọc {col_name}")
            popup.geometry("380x220")
            popup.attributes("-topmost", True)
            popup.transient(dialog)
            popup.grab_set()
            popup.focus_force()
            popup.resizable(False, False)
            ctk.CTkLabel(popup, text=f"Lọc theo {col_name}", font=("Inter", 14, "bold")).pack(pady=(18, 10))
            body = ctk.CTkFrame(popup, fg_color="transparent")
            body.pack(padx=20, pady=10, fill="x")

            def save():
                apply_current_filters()
                popup.destroy()

            if column_filters[col_name]["type"] == "text":
                entry = ctk.CTkEntry(body, width=320, placeholder_text="Nhập ký tự tìm kiếm...")
                entry.pack(pady=8)
                entry.insert(0, column_filters[col_name]["value"])
                def save_text():
                    column_filters[col_name]["value"] = entry.get().strip()
                    save()
                save_fn = save_text
            elif column_filters[col_name]["type"] == "number":
                min_ent = ctk.CTkEntry(body, width=140, placeholder_text="Min")
                max_ent = ctk.CTkEntry(body, width=140, placeholder_text="Max")
                min_ent.pack(side="left", padx=(0, 5))
                max_ent.pack(side="left", padx=(5, 0))
                if column_filters[col_name]["min"] is not None:
                    min_ent.insert(0, str(column_filters[col_name]["min"]))
                if column_filters[col_name]["max"] is not None:
                    max_ent.insert(0, str(column_filters[col_name]["max"]))
                def save_number():
                    try:
                        column_filters[col_name]["min"] = float(min_ent.get()) if min_ent.get().strip() else None
                        column_filters[col_name]["max"] = float(max_ent.get()) if max_ent.get().strip() else None
                    except ValueError:
                        column_filters[col_name]["min"] = None
                        column_filters[col_name]["max"] = None
                    save()
                save_fn = save_number
            elif column_filters[col_name]["type"] == "date":
                min_picker = DateEntry(body, width=14, background=PRIMARY_COLOR, foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
                max_picker = DateEntry(body, width=14, background=PRIMARY_COLOR, foreground="white", borderwidth=0, date_pattern="yyyy-mm-dd")
                min_picker.pack(side="left", padx=(0, 5))
                max_picker.pack(side="left", padx=(5, 0))
                if column_filters[col_name]["min"]:
                    min_picker.set_date(column_filters[col_name]["min"])
                if column_filters[col_name]["max"]:
                    max_picker.set_date(column_filters[col_name]["max"])
                def save_date():
                    column_filters[col_name]["min"] = min_picker.get_date() if min_picker.get() else None
                    column_filters[col_name]["max"] = max_picker.get_date() if max_picker.get() else None
                    save()
                save_fn = save_date
            else:
                combo = ctk.CTkComboBox(body, values=column_filters[col_name]["choices"], width=320)
                combo.set(column_filters[col_name]["value"])
                combo.pack(pady=8)
                def save_choice():
                    column_filters[col_name]["value"] = combo.get()
                    save()
                save_fn = save_choice

            btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
            btn_frame.pack(pady=12)
            ctk.CTkButton(btn_frame, text="Áp dụng", fg_color=PRIMARY_COLOR, width=120, command=save_fn).pack(side="left", padx=8)
            def clear_filter():
                if column_filters[col_name]["type"] == "text":
                    column_filters[col_name]["value"] = ""
                elif column_filters[col_name]["type"] in ["number", "date"]:
                    column_filters[col_name]["min"] = None
                    column_filters[col_name]["max"] = None
                else:
                    column_filters[col_name]["value"] = "All"
                refresh_tree([inv for inv in original_all_batch if batch_matches_filter(inv)])
                popup.destroy()
            ctk.CTkButton(btn_frame, text="Xoá lọc", fg_color="#fee2e2", text_color="#b91c1c", hover_color="#fca5a5", width=120, command=clear_filter).pack(side="left", padx=8)

        def apply_current_filters():
            refresh_tree([inv for inv in original_all_batch if batch_matches_filter(inv)])

        def on_header_click(event):
            if tree.identify_region(event.x, event.y) != "heading":
                return
            col = tree.identify_column(event.x)
            try:
                idx = int(col.replace("#", "")) - 1
                if idx in (0, 1):
                    return
                open_column_filter(cols[idx])
                return "break"
            except Exception:
                return

        tree.bind("<Button-1>", on_header_click)
        refresh_tree(original_all_batch)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
    
    def apply_product_filters(self, event=None):
        """Áp dụng bộ lọc cho danh sách sản phẩm"""
        if self.active_tab != "Product":
            return
        
        # Simply refresh the table - the filtering logic is now in refresh_table
        self.refresh_table()
    
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

    def open_task_manager_dialog(self):
        """Dialog quản lý transfer tasks"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Transfer Task Manager")
        dialog.geometry("1000x600")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Transfer Tasks", font=("Inter", 16, "bold")).pack(pady=(20, 10))

        # Frame chứa treeview
        tree_frame = ctk.CTkFrame(dialog, fg_color=BG_CARD)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Treeview hiển thị tasks
        cols = ("Task ID", "Product", "Source Batch", "Destination", "Quantity", "Priority", "Strategy", "Status", "Created At")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=20)
        for col in cols:
            tree.heading(col, text=col.upper())
            tree.column(col, anchor="center", width=100)
        tree.column("Task ID", width=80)
        tree.column("Product", width=120)
        tree.column("Source Batch", width=120)
        tree.column("Destination", width=180)
        tree.column("Quantity", width=80)
        tree.column("Priority", width=80)
        tree.column("Strategy", width=90)
        tree.column("Status", width=100)
        tree.column("Created At", width=120)

        # Thêm data
        tasks = self.service.get_all_tasks()
        for task in tasks:
            created_str = task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else ""
            dest_label = f"{task.target_location_type}:{task.target_location_id}" if task.target_location_type else task.target_location_id
            tree.insert("", "end", values=(task.task_id, task.product_id, task.source_batch_id, 
                                          dest_label, task.quantity, task.priority, task.strategy,
                                          task.status, created_str))

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame chứa buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        def execute_selected_task():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Vui lòng chọn 1 task để thực hiện!", parent=dialog)
                return
            
            item = tree.item(selected[0])
            task_id = item['values'][0]
            
            try:
                self.service.execute_transfer_task(task_id)
                messagebox.showinfo("Success", f"Đã thực hiện task {task_id} thành công!", parent=dialog)
                dialog.destroy()
                self.refresh_table()
                # Mở lại dialog để cập nhật
                self.open_task_manager_dialog()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi thực hiện task: {e}", parent=dialog)

        def cancel_selected_task():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Vui lòng chọn 1 task để hủy!", parent=dialog)
                return
            
            item = tree.item(selected[0])
            task_id = item['values'][0]
            
            if messagebox.askyesno("Confirm", f"Bạn có chắc muốn hủy task {task_id}?", parent=dialog):
                try:
                    self.service.cancel_task(task_id)
                    messagebox.showinfo("Success", f"Đã hủy task {task_id}", parent=dialog)
                    dialog.destroy()
                    self.open_task_manager_dialog()
                except Exception as e:
                    messagebox.showerror("Lỗi", f"Không thể hủy task: {e}", parent=dialog)

        ctk.CTkButton(btn_frame, text="Execute Task", fg_color="#10b981", hover_color="#059669",
                      font=("Inter", 12, "bold"), command=execute_selected_task).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(btn_frame, text="Cancel Task", fg_color="#ef4444", hover_color="#dc2626",
                      font=("Inter", 12, "bold"), command=cancel_selected_task).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(btn_frame, text="Refresh", fg_color="#6b7280", hover_color="#4b5563",
                      font=("Inter", 12, "bold"), command=lambda: [dialog.destroy(), self.open_task_manager_dialog()]).pack(side="right")


if __name__ == "__main__":
    app = App()
    app.mainloop()