from inventory_item import InventoryItem
from product import Product
from category import Category
import heapq # Thư viện chuẩn của Python cho cấu trúc dữ liệu Heap (Min-Heap)
from datetime import datetime, date # Thêm thư viện xử lý thời gian
from collections import deque # Thêm thư viện deque nếu cần dùng cho hàng đợi (Queue) trong tương lai

"""==================================================================================
Dịch vụ (Service Layer) - Lớp trung gian giữa giao diện người dùng và cơ sở dữ liệu.
- Chứa các phương thức để thực hiện các chức năng chính của hệ thống.
- Sử dụng các cấu trúc dữ liệu (DSA) như Hash Map (Dictionary) để lưu trữ dữ liệu trong RAM, giúp tăng tốc độ truy xuất và xử lý.
=================================================================================="""

#====================================================================
#Cây tiền tố Trie cho tìm kiếm sản phẩm theo tên
#====================================================================

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        # Lưu danh sách ID sản phẩm. 
        # (Dùng list vì có thể có nhiều sản phẩm trùng tên nhưng khác mã)
        self.product_ids = [] 

class ProductTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, name, product_id):
        """Thêm tên sản phẩm vào cây (O(L))"""
        node = self.root
        name = name.lower() # Chuyển về chữ thường để tìm kiếm không phân biệt hoa thường
        for char in name:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        
        node.is_end_of_word = True
        if product_id not in node.product_ids:
            node.product_ids.append(product_id)

    def _dfs(self, node, results):
        """Thuật toán Duyệt theo chiều sâu (DFS) để gom tất cả ID sản phẩm nhánh dưới"""
        if node.is_end_of_word:
            results.extend(node.product_ids)
        
        for child_node in node.children.values():
            self._dfs(child_node, results)

    def search_prefix(self, prefix):
        """Tìm kiếm các sản phẩm bắt đầu bằng tiền tố (O(L) + DFS)"""
        node = self.root
        prefix = prefix.lower()
        
        # Bước 1: Đi theo tiền tố
        for char in prefix:
            if char not in node.children:
                return [] # Không có sản phẩm nào khớp
            node = node.children[char]
            
        # Bước 2: Từ Node hiện tại, dùng DFS gom toàn bộ kết quả bên dưới
        results = []
        self._dfs(node, results)
        return results

#====================================================================
# Lớp Service chính của hệ thống
#====================================================================
class Service:
    def __init__(self):
        """
        Khởi tạo các cấu trúc dữ liệu (DSA) để lưu trữ trong RAM.
        Sử dụng Hash Map (Dictionary) giúp truy xuất dữ liệu theo ID với độ phức tạp O(1).
        """
        self.categories_map = {}  # Key: id_danh_mục, Value: Đối tượng Category
        self.products_map = {}    # Key: id_sản_phẩm, Value: Đối tượng Product
        self.inventory_map = {}   # Key: id_bản_ghi_kho, Value: Đối tượng InventoryItem
        # Thêm Map mới: Đóng vai trò là Secondary Index (Chỉ mục phụ)
        # Key: (product_id, batch_id, mfg_date, exp_date, warehouse_id) -> Value: InventoryItem
        self.inventory_composite_map = {}
		# THÊM MỚI: Khởi tạo Trie
        self.product_trie = ProductTrie()
        # THÊM MỚI: Hàng đợi (Queue) giới hạn 5 phần tử cho lịch sử xem
        self.recently_viewed = deque(maxlen=5)

    # =========================================================================
    # 1. TẢI DỮ LIỆU (LOAD DATA FROM DATABASE TO RAM)
    # =========================================================================
    
    def load_data(self, cursor):
        """
        Đọc toàn bộ dữ liệu từ MySQL và nạp vào các Dictionary trong RAM.
        Đây là kỹ thuật Caching để tăng tốc độ xử lý cho các chức năng tìm kiếm/hiển thị.
        """
        self.categories_map.clear()
        self.products_map.clear()
        self.inventory_map.clear()
        self.inventory_composite_map.clear() # Clear map mới
        self.product_trie = ProductTrie() # Reset Trie mới

        # Load Danh mục (Categories)
        cursor.execute("SELECT * FROM categories")
        for row in cursor.fetchall():
            cat = Category(row[0], row[1])
            self.categories_map[cat.id] = cat

        # Load Sản phẩm (Products)
        cursor.execute("SELECT * FROM products")
        for row in cursor.fetchall():
            prod = Product(*row)
            self.products_map[prod.id] = prod
            self.product_trie.insert(prod.name, prod.id) # Nạp vào Cây tiền tố
        
        # Load Kho hàng (Inventory)
        cursor.execute("SELECT * FROM inventory")
        for row in cursor.fetchall():
            item = InventoryItem(*row)
            self.inventory_map[item.id] = item
            # Khởi tạo Composite Key dạng Tuple. 
            # Lưu ý: Ép kiểu mfg_date và exp_date về string để so sánh nhất quán
            comp_key = (item.product_id, item.batch_id, str(item.mfg_date), str(item.exp_date), item.warehouse_id)
            self.inventory_composite_map[comp_key] = item
            
			
    # =========================================================================
    # 2. QUẢN LÝ DANH MỤC (CATEGORY MANAGEMENT)
    # =========================================================================

    def add_category(self, id, name, cursor, conn):
        """Thêm danh mục mới vào DB và cập nhật vào Hash Map RAM"""
        if id in self.categories_map:
            return False # ID đã tồn tại
        
        cursor.execute("INSERT INTO categories (id, name) VALUES (%s, %s)", (id, name))
        conn.commit()
        
        # Cập nhật RAM (O(1))
        self.categories_map[id] = Category(id, name)
        return True

    def show_categories(self):
        """Trả về danh sách tất cả danh mục từ RAM (O(n))"""
        return list(self.categories_map.values())

    # =========================================================================
    # 3. QUẢN LÝ SẢN PHẨM (PRODUCT MANAGEMENT)
    # =========================================================================

    def check_product_exist(self, product_id):
        """Kiểm tra sản phẩm tồn tại trong RAM (O(1))"""
        return self.products_map.get(product_id, None)

    def add_product(self, id, name, category_id, price, status, cursor, conn):
        """Thêm sản phẩm mới kèm theo kiểm tra tính hợp lệ của Danh mục"""
        # Kiểm tra ID sản phẩm trùng
        if self.check_product_exist(id):
            return False
        
        # DSA Check: Kiểm tra danh mục có tồn tại trong RAM không (O(1))
        # Đây là quy tắc ràng buộc dữ liệu (Data Integrity)
        if category_id not in self.categories_map:
            return False

		# Lưu vào Database
        cursor.execute("INSERT INTO products (id, name, category_id, price, status) VALUES (%s, %s, %s, %s, %s)", 
                       (id, name, category_id, price, status))
        conn.commit()
        
        # Cập nhật RAM và Trie
        product = Product(id, name, category_id, price, status)
        self.products_map[id] = product
        self.product_trie.insert(name, id) # Cập nhật vào cây ngay lập tức
        return True

    def find_product_by_id(self, id):
        """Tìm nhanh sản phẩm theo ID (O(1))"""
        product = self.products_map.get(id, None)
        if product:
            # Thuật toán LRU Cache cơ bản: 
            # Nếu sản phẩm đã có trong lịch sử, xóa nó ở vị trí cũ...
            if id in self.recently_viewed:
                self.recently_viewed.remove(id)
            # ...và đẩy nó lên cuối hàng đợi (tức là mới nhất)
            self.recently_viewed.append(id)
        return product

    def show_products(self):
        """Lấy toàn bộ danh sách sản phẩm từ RAM"""
        return list(self.products_map.values())

    # =========================================================================
    # 4. QUẢN LÝ KHO HÀNG (INVENTORY MANAGEMENT)
    # =========================================================================

    def check_item_exist(self, product_id, batch_id, mfg_date, exp_date, warehouse_id):
        """
        [CẬP NHẬT DSA]: Tìm kiếm O(1) bằng cách sử dụng Composite Key.
        Thay vì dùng vòng lặp O(n) như trước.
        """
        comp_key = (product_id, batch_id, str(mfg_date), str(exp_date), warehouse_id)
        return self.inventory_composite_map.get(comp_key, None)

    def add_inventory_item(self, product_id, quantity, batch_id, mfg_date, exp_date, warehouse_id, cursor, conn):
        existing = self.check_item_exist(product_id, batch_id, mfg_date, exp_date, warehouse_id)
        
        if existing:
            # 1. Cập nhật số lượng (Object reference sẽ tự động cập nhật ở cả 2 Map)
            existing.update_quantity(quantity)
            cursor.execute("UPDATE inventory SET quantity = %s WHERE id = %s", (existing.quantity, existing.id))
            conn.commit()
            return True
        else:
            # 2. Thêm mới
            cursor.execute("INSERT INTO inventory (product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id) "
                           "VALUES (%s, %s, %s, %s, %s, %s)", 
                           (product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id))
            conn.commit()
            
            item_id = cursor.lastrowid
            new_item = InventoryItem(item_id, product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id)
            
            # Cập nhật vào CẢ 2 HASH MAPS
            self.inventory_map[item_id] = new_item
            comp_key = (product_id, batch_id, str(mfg_date), str(exp_date), warehouse_id)
            self.inventory_composite_map[comp_key] = new_item
            
            return True

    def find_inventory_by_product_id(self, product_id):
        """Lọc danh sách các lô hàng của một sản phẩm cụ thể (O(n))"""
        return [item for item in self.inventory_map.values() if item.product_id == product_id]
            
    def show_inventory(self):
        """Hiển thị tất cả các lô hàng có trong kho"""
        return list(self.inventory_map.values())

    # =========================================================================
    # 5. CÁC GIẢI THUẬT SẮP XẾP VÀ TÌM KIẾM NÂNG CAO
    # =========================================================================
    def get_low_stock_warnings(self, threshold=50):
        """
        Thuật toán cảnh báo sắp hết hàng sử dụng Hash Map và Min-Heap.
        - threshold: Ngưỡng số lượng tồn kho tối thiểu để báo động (Mặc định: 50)
        """
        # Bước 1: Tính tổng tồn kho cho từng sản phẩm (Gom nhóm O(n))
        stock_summary = {}
        for item in self.inventory_map.values():
            stock_summary[item.product_id] = stock_summary.get(item.product_id, 0) + item.quantity

        # Bổ sung các sản phẩm chưa từng có trong kho (số lượng = 0)
        for prod_id in self.products_map.keys():
            if prod_id not in stock_summary:
                stock_summary[prod_id] = 0

        # Bước 2: Sử dụng Min-Heap để lọc và sắp xếp
        min_heap = []
        for prod_id, total_qty in stock_summary.items():
            if total_qty <= threshold:
                # Đẩy vào Min-Heap dạng Tuple: (Tiêu_chí_sắp_xếp, Giá_trị_đi_kèm)
                # Ở đây là (total_qty, prod_id)
                heapq.heappush(min_heap, (total_qty, prod_id))

        # Bước 3: Rút trích kết quả từ Heap (Từ ít nhất đến nhiều nhất)
        warnings = []
        while min_heap:
            qty, prod_id = heapq.heappop(min_heap) # Lấy phần tử nhỏ nhất ra
            product = self.products_map[prod_id]
            warnings.append({
                "id": product.id,
                "name": product.name,
                "total_quantity": qty
            })

        return warnings 

    def get_expiring_soon_warnings(self, days_threshold=30):
        """
        Lọc và sắp xếp các lô hàng sắp hết hạn sử dụng.
        - days_threshold: Ngưỡng số ngày báo động (Mặc định: 30 ngày)
        """
        today = date.today()
        min_heap = []

        # Bước 1: Quét qua toàn bộ kho hàng (O(n))
        for item in self.inventory_map.values():
            # Xử lý an toàn: Tùy thư viện kết nối, exp_date có thể là chuỗi hoặc đối tượng date
            if isinstance(item.exp_date, str):
                exp_date_obj = datetime.strptime(item.exp_date, "%Y-%m-%d").date()
            else:
                exp_date_obj = item.exp_date

            # Tính số ngày còn lại
            days_remaining = (exp_date_obj - today).days

            # Lọc các sản phẩm <= ngưỡng báo động (bao gồm cả số âm là ĐÃ HẾT HẠN)
            if days_remaining <= days_threshold:
                # [Mẹo DSA Python]: Push vào Heap dạng Tuple (days_remaining, item.id, item)
                # item.id đóng vai trò "tie-breaker". Nếu 2 lô hàng có cùng ngày hết hạn,
                # Heap sẽ so sánh đến ID (là số nguyên duy nhất) để tránh lỗi crash chương trình.
                heapq.heappush(min_heap, (days_remaining, item.id, item))

        # Bước 2: Rút trích kết quả từ Heap ra danh sách (O(k log k))
        warnings = []
        while min_heap:
            days_left, _, item = heapq.heappop(min_heap)
            product = self.products_map.get(item.product_id)
            
            warnings.append({
                "inv_id": item.id,
                "batch_id": item.batch_id,
                "product_name": product.name if product else "Unknown",
                "exp_date": item.exp_date,
                "days_left": days_left,
                "quantity": item.quantity,
                "warehouse_id": item.warehouse_id
            })

        return warnings
    

    # ---	TÌM KIẾM SẢN PHẨM THEO TÊN (AUTO-COMPLETE BẰNG TRIE)  ---
    def search_products_by_name(self, prefix):
        """Hàm giao tiếp với UI để lấy thông tin chi tiết các sản phẩm tìm được"""
        if not prefix.strip():
            return []
            
        product_ids = self.product_trie.search_prefix(prefix)
        
        # Map từ ID sang Object Product
        matched_products = [self.products_map[pid] for pid in product_ids]
        return matched_products
    
    # --- LẤY DANH SÁCH XEM GẦN ĐÂY (QUEUE / DEQUE)  ---
    def get_recently_viewed_products(self):
        """Trả về danh sách sản phẩm đã xem từ mới nhất -> cũ nhất"""
        recent_products = []
        # Duyệt ngược hàng đợi để hiển thị cái mới nhất trước
        for pid in reversed(self.recently_viewed):
            recent_products.append(self.products_map.get(pid))
        return recent_products