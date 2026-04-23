import tkinter as tk
from tkinter import ttk, messagebox
import db_connect
from service import Service

class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hệ thống Quản lý Kho & Cửa hàng (DSA Powered)")
        self.root.geometry("900x600")
        
        # Khởi tạo Service và kết nối Database
        self.conn = db_connect.get_connection()
        self.cursor = self.conn.cursor()
        # Chỉ cần gọi Service là đủ vì mọi Hash Map/Trie đều nằm trong này
        self.service = Service()
        
        # Tải dữ liệu từ DB lên RAM (Hash Map, Trie, v.v.)
        try:
            self.service.load_data(self.cursor)
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải dữ liệu: {e}")

        # Tạo thanh điều hướng dạng Tab (Notebook)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True, fill='both')

        # Khởi tạo các Tab
        self.tab_product = ttk.Frame(self.notebook)
        self.tab_inventory = ttk.Frame(self.notebook)
        self.tab_search = ttk.Frame(self.notebook)
        self.tab_alerts = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_product, text='Thêm Sản phẩm/Nhập kho')
        self.notebook.add(self.tab_inventory, text='Bảng Tồn kho')
        self.notebook.add(self.tab_search, text='🔍 Tìm kiếm (Trie)')
        self.notebook.add(self.tab_alerts, text='⚠️ Cảnh báo (Heap)')

        # Gọi hàm xây dựng giao diện cho từng Tab
        self.build_tab_search()  # Xây dựng thử Tab Tìm kiếm trước
        
        # Xử lý sự kiện khi đóng cửa sổ
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ==========================================
    # XÂY DỰNG GIAO DIỆN TAB TÌM KIẾM (DEMO)
    # ==========================================
    def build_tab_search(self):
        # Khu vực nhập liệu (Top)
        frame_top = tk.Frame(self.tab_search, pady=10)
        frame_top.pack(fill='x')

        tk.Label(frame_top, text="Nhập tên sản phẩm (Auto-complete):", font=('Arial', 12)).pack(side='left', padx=10)
        
        self.entry_search = ttk.Entry(frame_top, font=('Arial', 12), width=40)
        self.entry_search.pack(side='left', padx=10)
        
        # Bắt sự kiện mỗi khi người dùng gõ phím (Key Release)
        self.entry_search.bind('<KeyRelease>', self.on_search_typing)

        # Bảng hiển thị kết quả (Bottom)
        columns = ("ID", "Tên Sản phẩm", "Giá bán", "Trạng thái")
        self.tree_search = ttk.Treeview(self.tab_search, columns=columns, show="headings", height=20)
        
        # Cấu hình cột
        self.tree_search.heading("ID", text="Mã SP")
        self.tree_search.column("ID", width=100)
        self.tree_search.heading("Tên Sản phẩm", text="Tên Sản phẩm")
        self.tree_search.column("Tên Sản phẩm", width=400)
        self.tree_search.heading("Giá bán", text="Giá bán")
        self.tree_search.column("Giá bán", width=100)
        self.tree_search.heading("Trạng thái", text="Trạng thái")
        
        self.tree_search.pack(pady=10, padx=10, fill='both', expand=True)

    # ==========================================
    # LOGIC XỬ LÝ SỰ KIỆN
    # ==========================================
    def on_search_typing(self, event):
        """Kích hoạt Trie Search mỗi khi gõ phím"""
        keyword = self.entry_search.get()
        
        # Xóa dữ liệu cũ trong bảng
        for item in self.tree_search.get_children():
            self.tree_search.delete(item)
            
        if not keyword.strip():
            return
            
        # Gọi hàm Trie từ service
        results = self.service.search_products_by_name(keyword)
        
        # Đổ dữ liệu mới vào bảng
        for p in results:
            self.tree_search.insert("", tk.END, values=(p.id, p.name, f"${p.price:.2f}", p.status))

    def on_closing(self):
        """Đóng kết nối an toàn khi tắt app"""
        self.cursor.close()
        self.conn.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()