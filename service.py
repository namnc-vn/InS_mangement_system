import heapq
from datetime import datetime, date
from collections import deque

from inventory_item import InventoryItem
from product import Product
from category import Category
from warehouse import Warehouse
from store import Store

# ==========================================
# 1. TRIE — Auto-complete theo ID (product_id, batch_id)
# ==========================================
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for char in str(word):
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True

    def get_suggestions(self, prefix):
        """Lấy các từ bắt đầu bằng prefix — O(L + V)"""
        node = self.root
        for char in str(prefix):
            if char not in node.children:
                return []
            node = node.children[char]
        results = []
        self._dfs(node, str(prefix), results)
        return results

    def _dfs(self, node, current_word, results):
        if node.is_end:
            results.append(current_word)
        for char, child_node in node.children.items():
            self._dfs(child_node, current_word + char, results)


# ==========================================
# 2. ProductTrie — Tìm kiếm theo TÊN sản phẩm
# ==========================================
class ProductTrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.product_ids = []

class ProductTrie:
    def __init__(self):
        self.root = ProductTrieNode()

    def insert(self, name, product_id):
        """Thêm tên sản phẩm vào cây — O(L)"""
        node = self.root
        for char in name.lower():
            if char not in node.children:
                node.children[char] = ProductTrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        if product_id not in node.product_ids:
            node.product_ids.append(product_id)

    def _dfs(self, node, results):
        """DFS gom tất cả product_id bên dưới node"""
        if node.is_end_of_word:
            results.extend(node.product_ids)
        for child in node.children.values():
            self._dfs(child, results)

    def search_prefix(self, prefix):
        """Tìm các sản phẩm có tên bắt đầu bằng prefix — O(L + DFS)"""
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]
        results = []
        self._dfs(node, results)
        return results


# ==========================================
# 3. KMP Search — Tìm kiếm chuỗi con
# ==========================================
def compute_lps(pattern):
    lps = [0] * len(pattern)
    length = 0
    i = 1
    while i < len(pattern):
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        else:
            if length != 0:
                length = lps[length - 1]
            else:
                lps[i] = 0
                i += 1
    return lps

def kmp_search(text, pattern):
    if not pattern:
        return True
    text, pattern = str(text).lower(), str(pattern).lower()
    lps = compute_lps(pattern)
    i = j = 0
    while i < len(text):
        if pattern[j] == text[i]:
            i += 1
            j += 1
        if j == len(pattern):
            return True
        elif i < len(text) and pattern[j] != text[i]:
            if j != 0:
                j = lps[j - 1]
            else:
                i += 1
    return False


# ==========================================
# 4. BST — Range search theo số lượng tồn kho
# ==========================================
class BSTNode:
    def __init__(self, key, item):
        self.key = key
        self.items = [item]
        self.left = self.right = None

class InventoryBST:
    def __init__(self):
        self.root = None

    def insert(self, key, item):
        if self.root is None:
            self.root = BSTNode(key, item)
        else:
            self._insert(self.root, key, item)

    def _insert(self, node, key, item):
        if key == node.key:
            node.items.append(item)
        elif key < node.key:
            if node.left is None:
                node.left = BSTNode(key, item)
            else:
                self._insert(node.left, key, item)
        else:
            if node.right is None:
                node.right = BSTNode(key, item)
            else:
                self._insert(node.right, key, item)

    def range_search(self, min_val, max_val):
        """Tìm tất cả lô hàng có quantity trong [min_val, max_val]"""
        results = []
        self._search(self.root, min_val, max_val, results)
        return results

    def _search(self, node, min_val, max_val, results):
        if not node:
            return
        if min_val <= node.key <= max_val:
            results.extend(node.items)
        if min_val < node.key:
            self._search(node.left, min_val, max_val, results)
        if node.key < max_val:
            self._search(node.right, min_val, max_val, results)


# ==========================================
# 5. SERVICE — Lớp nghiệp vụ chính
# ==========================================
class Service:
    def __init__(self):
        # --- Hash Maps (O(1) lookup) ---
        self.categories_map = {}
        self.products_map = {}
        self.inventory_map = {}
        self.inventory_composite_map = {}   # Composite key → chống trùng lô hàng
        self.warehouses_map = {}
        self.stores_map = {}

        # --- DSA nâng cao ---
        self.qty_bst = InventoryBST()           # BST range search
        self.product_id_trie = Trie()           # Autocomplete Product ID
        self.batch_id_trie = Trie()             # Autocomplete Batch ID
        self.product_name_trie = ProductTrie()  # Search sản phẩm theo tên

        # --- Deque: Lịch sử 5 sản phẩm vừa xem (LRU Cache đơn giản) ---
        self.recently_viewed = deque(maxlen=5)

        self.settings = {
            "low_stock_threshold": 15,
            "expiring_days_threshold": 30
        }

    # =========================================================================
    # TẢI DỮ LIỆU
    # =========================================================================
    def load_data(self, cursor):
        """Nạp toàn bộ DB vào RAM — Cache để tăng tốc truy xuất"""
        self.categories_map.clear()
        self.products_map.clear()
        self.inventory_map.clear()
        self.inventory_composite_map.clear()
        self.warehouses_map.clear()
        self.stores_map.clear()
        self.qty_bst = InventoryBST()
        self.product_id_trie = Trie()
        self.batch_id_trie = Trie()
        self.product_name_trie = ProductTrie()

        cursor.execute("SELECT * FROM categories")
        for row in cursor.fetchall():
            cat = Category(row[0], row[1])
            self.categories_map[cat.id] = cat

        cursor.execute("SELECT * FROM products")
        for row in cursor.fetchall():
            prod = Product(*row)
            self.products_map[prod.id] = prod
            self.product_id_trie.insert(prod.id)
            self.product_name_trie.insert(prod.name, prod.id)

        cursor.execute("SELECT * FROM inventory")
        for row in cursor.fetchall():
            item = InventoryItem(*row)
            self.inventory_map[item.id] = item
            comp_key = (item.product_id, item.batch_id,
                        str(item.mfg_date), str(item.exp_date), item.warehouse_id, item.store_id)
            self.inventory_composite_map[comp_key] = item
            self.qty_bst.insert(item.quantity, item)
            self.batch_id_trie.insert(item.batch_id)

        try:
            cursor.execute("SELECT * FROM warehouses")
            for row in cursor.fetchall():
                wh = Warehouse(row[0], row[1], row[2])
                self.warehouses_map[wh.id] = wh
        except Exception:
            pass  # Bảng warehouses chưa tồn tại thì bỏ qua

        try:
            cursor.execute("SELECT * FROM stores")
            for row in cursor.fetchall():
                st = Store(row[0], row[1], row[2])
                self.stores_map[st.id] = st
        except Exception:
            pass

    def _get_next_id(self, item_dict, prefix):
        max_num = 0
        for item_id in item_dict.keys():
            if item_id.startswith(prefix):
                try:
                    num = int(item_id[len(prefix):])
                    if num > max_num: max_num = num
                except ValueError:
                    pass
        return f"{prefix}{max_num + 1:02d}"

    # =========================================================================
    # CATEGORY
    # =========================================================================
    def generate_category_id(self):
        return self._get_next_id(self.categories_map, "C")

    def add_category(self, id, name, cursor, conn):
        """Thêm danh mục mới — kiểm tra trùng ID bằng Hash Map O(1)"""
        if id in self.categories_map:
            return False
        cursor.execute("INSERT INTO categories (id, name) VALUES (%s, %s)", (id, name))
        conn.commit()
        self.categories_map[id] = Category(id, name)
        return True

    def show_categories(self):
        return list(self.categories_map.values())

    # =========================================================================
    # PRODUCT
    # =========================================================================
    def check_product_exist(self, product_id):
        """Kiểm tra sản phẩm tồn tại — O(1)"""
        return self.products_map.get(product_id, None)

    def add_product(self, prod_id, name, category_id, price, status, cursor, conn):
        """Thêm sản phẩm mới + cập nhật Trie"""
        if prod_id in self.products_map:
            return False
        cursor.execute(
            "INSERT INTO products (id, name, category_id, price, status) VALUES (%s, %s, %s, %s, %s)",
            (prod_id, name, category_id, price, status)
        )
        conn.commit()
        new_prod = Product(prod_id, name, category_id, price, status)
        self.products_map[prod_id] = new_prod
        self.product_id_trie.insert(prod_id)
        self.product_name_trie.insert(name, prod_id)
        return True

    def find_product_by_id(self, id):
        """Tìm theo ID — O(1) + ghi lịch sử xem (Deque / LRU)"""
        product = self.products_map.get(id, None)
        if product:
            if id in self.recently_viewed:
                self.recently_viewed.remove(id)
            self.recently_viewed.append(id)
        return product

    def show_products(self):
        return list(self.products_map.values())

    def search_products_by_name(self, prefix):
        """Tìm kiếm theo tên bằng ProductTrie — O(L + DFS)"""
        if not prefix.strip():
            return []
        ids = self.product_name_trie.search_prefix(prefix)
        return [self.products_map[pid] for pid in ids if pid in self.products_map]

    def get_recently_viewed_products(self):
        """Lấy lịch sử 5 sản phẩm vừa xem — Deque"""
        return [self.products_map.get(pid) for pid in reversed(self.recently_viewed)]

    # =========================================================================
    # INVENTORY
    # =========================================================================
    def check_item_exist(self, product_id, batch_id, mfg_date, exp_date, warehouse_id, store_id=None):
        """Kiểm tra lô hàng đã tồn tại bằng Composite Key — O(1)"""
        comp_key = (product_id, batch_id, str(mfg_date), str(exp_date), warehouse_id, store_id)
        return self.inventory_composite_map.get(comp_key, None)

    def add_inventory_item(self, product_id, quantity, batch_id, mfg_date, exp_date, warehouse_id, cursor, conn, store_id=None):
        existing = self.check_item_exist(product_id, batch_id, mfg_date, exp_date, warehouse_id, store_id)
        if existing:
            existing.quantity += int(quantity)
            cursor.execute("UPDATE inventory SET quantity = %s WHERE id = %s",
                           (existing.quantity, existing.id))
            conn.commit()
            return True, existing.id
        else:
            cursor.execute(
                "INSERT INTO inventory (product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id, store_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id, store_id)
            )
            conn.commit()
            item_id = cursor.lastrowid
            new_item = InventoryItem(item_id, product_id, batch_id, mfg_date,
                                     exp_date, int(quantity), warehouse_id, store_id)
            self.inventory_map[item_id] = new_item
            comp_key = (product_id, batch_id, str(mfg_date), str(exp_date), warehouse_id, store_id)
            self.inventory_composite_map[comp_key] = new_item
            self.qty_bst.insert(int(quantity), new_item)
            self.batch_id_trie.insert(batch_id)
            return True, item_id

    def find_inventory_by_product_id(self, product_id):
        return [item for item in self.inventory_map.values() if item.product_id == product_id]

    def show_inventory(self):
        return list(self.inventory_map.values())

    # =========================================================================
    # WAREHOUSE
    # =========================================================================
    def generate_warehouse_id(self):
        return self._get_next_id(self.warehouses_map, "WH-")

    def add_warehouse(self, wh_id, name, space, cursor, conn):
        if wh_id in self.warehouses_map:
            return False
        cursor.execute("INSERT INTO warehouses (id, name, space) VALUES (%s, %s, %s)",
                       (wh_id, name, space))
        conn.commit()
        self.warehouses_map[wh_id] = Warehouse(wh_id, name, space)
        return True

    def get_warehouse_summary(self):
        """Thống kê lô hàng & tổng số lượng theo từng kho — O(n) Hash Map"""
        summary = {}
        for inv in self.inventory_map.values():
            if inv.warehouse_id:
                wh_id = inv.warehouse_id
                if wh_id not in summary:
                    summary[wh_id] = {"batches": 0, "total_qty": 0}
                summary[wh_id]["batches"] += 1
                summary[wh_id]["total_qty"] += inv.quantity
        return summary

    # =========================================================================
    # STORE
    # =========================================================================
    def generate_store_id(self):
        return self._get_next_id(self.stores_map, "ST-")

    def add_store(self, store_id, name, location, cursor, conn):
        if store_id in self.stores_map:
            return False
        cursor.execute("INSERT INTO stores (id, name, location) VALUES (%s, %s, %s)",
                       (store_id, name, location))
        conn.commit()
        self.stores_map[store_id] = Store(store_id, name, location)
        return True

    def get_store_summary(self):
        summary = {}
        for inv in self.inventory_map.values():
            if inv.store_id:
                st_id = inv.store_id
                if st_id not in summary:
                    summary[st_id] = {"batches": 0, "total_qty": 0}
                summary[st_id]["batches"] += 1
                summary[st_id]["total_qty"] += inv.quantity
        return summary

    def transfer_inventory(self, item_id, target_store_id, transfer_qty, cursor, conn):
        """Chuyển số lượng từ lô hàng trong Warehouse sang Store"""
        source_item = self.inventory_map.get(item_id)
        if not source_item or source_item.quantity < transfer_qty:
            return False, "Not enough quantity"
        
        # 1. Trừ số lượng kho (nếu = 0 thì xóa trong service, DB thì delete)
        source_item.quantity -= transfer_qty
        if source_item.quantity > 0:
            cursor.execute("UPDATE inventory SET quantity = %s WHERE id = %s", (source_item.quantity, item_id))
        else:
            cursor.execute("DELETE FROM inventory WHERE id = %s", (item_id,))
            self.inventory_map.pop(item_id)
            comp_key = (source_item.product_id, source_item.batch_id, str(source_item.mfg_date), str(source_item.exp_date), source_item.warehouse_id, source_item.store_id)
            self.inventory_composite_map.pop(comp_key, None)
        conn.commit()

        # 2. Thêm vào cửa hàng
        _, target_item_id = self.add_inventory_item(
            source_item.product_id, transfer_qty, source_item.batch_id, 
            source_item.mfg_date, source_item.exp_date, None, cursor, conn, store_id=target_store_id
        )
        return True, target_item_id

    # =========================================================================
    # ALERTS — Heap-based
    # =========================================================================
    def get_low_stock_warnings(self, threshold=50):
        """Cảnh báo sắp hết hàng — Min-Heap O(n log k)"""
        stock_summary = {}
        for item in self.inventory_map.values():
            stock_summary[item.product_id] = stock_summary.get(item.product_id, 0) + item.quantity
        for prod_id in self.products_map.keys():
            if prod_id not in stock_summary:
                stock_summary[prod_id] = 0

        min_heap = []
        for prod_id, total_qty in stock_summary.items():
            if total_qty <= threshold:
                heapq.heappush(min_heap, (total_qty, prod_id))

        warnings = []
        while min_heap:
            qty, prod_id = heapq.heappop(min_heap)
            product = self.products_map[prod_id]
            warnings.append({"id": product.id, "name": product.name, "total_quantity": qty})
        return warnings

    def get_expiring_soon_warnings(self, days_threshold=30):
        """Cảnh báo sắp hết hạn — Min-Heap O(n log k)"""
        today = date.today()
        min_heap = []
        for item in self.inventory_map.values():
            if isinstance(item.exp_date, str):
                exp_obj = datetime.strptime(item.exp_date, "%Y-%m-%d").date()
            else:
                exp_obj = item.exp_date
            days_left = (exp_obj - today).days
            if days_left <= days_threshold:
                heapq.heappush(min_heap, (days_left, item.id, item))

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

    def get_low_stock_items(self):
        """Lấy danh sách lô hàng thấp — dùng cho GUI"""
        threshold = self.settings["low_stock_threshold"]
        min_heap = []
        for inv in self.inventory_map.values():
            if inv.quantity <= threshold:
                heapq.heappush(min_heap, (inv.quantity, inv.id, inv))
        return [heapq.heappop(min_heap)[2] for _ in range(len(min_heap))]

    def get_expiring_items(self):
        """Lấy danh sách lô sắp hết hạn — dùng cho GUI"""
        threshold = self.settings["expiring_days_threshold"]
        today = date.today()
        min_heap = []
        for inv in self.inventory_map.values():
            try:
                exp = (datetime.strptime(str(inv.exp_date), "%Y-%m-%d").date()
                       if isinstance(inv.exp_date, str) else inv.exp_date)
                days_left = (exp - today).days
                if days_left <= threshold:
                    heapq.heappush(min_heap, (days_left, inv.id, inv))
            except Exception:
                pass
        return [heapq.heappop(min_heap)[2] for _ in range(len(min_heap))]

    # =========================================================================
    # SEARCH (KMP) & KPI
    # =========================================================================
    def search_items(self, keyword, item_type="Product"):
        """Tìm kiếm bằng KMP Search — O(n * (m + p))"""
        results = []
        if item_type == "Product":
            source = self.products_map.values() if not keyword.strip() else [
                p for p in self.products_map.values()
                if kmp_search(p.name, keyword) or kmp_search(str(p.id), keyword)
            ]
            return list(source) if not keyword.strip() else source
        elif item_type == "Inventory":
            if not keyword.strip():
                return list(self.inventory_map.values())
            for inv in self.inventory_map.values():
                prod_name = getattr(self.products_map.get(inv.product_id), 'name', str(inv.product_id))
                if kmp_search(prod_name, keyword) or kmp_search(str(inv.batch_id), keyword):
                    results.append(inv)
        elif item_type == "Category":
            if not keyword.strip():
                return list(self.categories_map.values())
            for c in self.categories_map.values():
                if kmp_search(c.name, keyword) or kmp_search(str(c.id), keyword):
                    results.append(c)
        elif item_type == "Warehouse":
            if not keyword.strip():
                return list(self.warehouses_map.values())
            for w in self.warehouses_map.values():
                if kmp_search(w.name, keyword) or kmp_search(str(w.id), keyword):
                    results.append(w)
        elif item_type == "Store":
            if not keyword.strip():
                return list(self.stores_map.values())
            for s in self.stores_map.values():
                if kmp_search(s.name, keyword) or kmp_search(str(s.id), keyword):
                    results.append(s)
        return results

    # =========================================================================
    # REMOVE / RESTORE — Dùng cho Command Pattern (Undo / Redo)
    # Nguyên tắc: history.py chỉ gọi service, không tự gọi DB trực tiếp
    # =========================================================================

    # --- INVENTORY ---
    def remove_inventory_item(self, item_id, cursor, conn):
        """Xóa lô hàng khỏi DB và cập nhật RAM — dùng cho Undo AddInventory"""
        cursor.execute("DELETE FROM inventory WHERE id=%s", (item_id,))
        conn.commit()
        item = self.inventory_map.pop(item_id, None)
        if item:
            comp_key = (item.product_id, item.batch_id,
                        str(item.mfg_date), str(item.exp_date), item.warehouse_id, item.store_id)
            self.inventory_composite_map.pop(comp_key, None)
        return item

    def restore_inventory_item(self, item_id, product_id, batch_id,
                               mfg_date, exp_date, quantity, warehouse_id, cursor, conn, store_id=None):
        """Chèn lại lô hàng với ID cũ — dùng cho Redo AddInventory"""
        cursor.execute(
            "INSERT INTO inventory (id, product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id, store_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (item_id, product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id, store_id)
        )
        conn.commit()
        new_item = InventoryItem(item_id, product_id, batch_id,
                                  mfg_date, exp_date, quantity, warehouse_id, store_id)
        self.inventory_map[item_id] = new_item
        comp_key = (product_id, batch_id, str(mfg_date), str(exp_date), warehouse_id, store_id)
        self.inventory_composite_map[comp_key] = new_item
        self.qty_bst.insert(quantity, new_item)

    def update_inventory_quantity(self, item_id, new_quantity, cursor, conn):
        """Cập nhật số lượng một lô hàng — dùng cho Undo/Redo UpdateQty"""
        item = self.inventory_map.get(item_id)
        if item:
            item.quantity = new_quantity
            cursor.execute("UPDATE inventory SET quantity=%s WHERE id=%s",
                           (new_quantity, item_id))
            conn.commit()
            return True
        return False

    # --- PRODUCT ---
    def remove_product(self, prod_id, cursor, conn):
        """Xóa sản phẩm khỏi DB và RAM — dùng cho Undo AddProduct"""
        cursor.execute("DELETE FROM products WHERE id=%s", (prod_id,))
        conn.commit()
        self.products_map.pop(prod_id, None)

    def restore_product(self, prod_id, name, category_id, price, status, cursor, conn):
        """Chèn lại sản phẩm — dùng cho Redo AddProduct"""
        cursor.execute(
            "INSERT INTO products (id, name, category_id, price, status) VALUES (%s,%s,%s,%s,%s)",
            (prod_id, name, category_id, price, status)
        )
        conn.commit()
        new_prod = Product(prod_id, name, category_id, price, status)
        self.products_map[prod_id] = new_prod
        self.product_id_trie.insert(prod_id)
        self.product_name_trie.insert(name, prod_id)

    # --- CATEGORY ---
    def remove_category(self, cat_id, cursor, conn):
        """Xóa danh mục khỏi DB và RAM — dùng cho Undo AddCategory"""
        cursor.execute("DELETE FROM categories WHERE id=%s", (cat_id,))
        conn.commit()
        self.categories_map.pop(cat_id, None)

    def restore_category(self, cat_id, name, cursor, conn):
        """Chèn lại danh mục — dùng cho Redo AddCategory"""
        cursor.execute("INSERT INTO categories (id, name) VALUES (%s,%s)", (cat_id, name))
        conn.commit()
        self.categories_map[cat_id] = Category(cat_id, name)

    # --- WAREHOUSE ---
    def remove_warehouse(self, wh_id, cursor, conn):
        """Xóa kho khỏi DB và RAM — dùng cho Undo AddWarehouse"""
        cursor.execute("DELETE FROM warehouses WHERE id=%s", (wh_id,))
        conn.commit()
        self.warehouses_map.pop(wh_id, None)

    def restore_warehouse(self, wh_id, name, space, cursor, conn):
        """Chèn lại kho — dùng cho Redo AddWarehouse"""
        cursor.execute("INSERT INTO warehouses (id, name, space) VALUES (%s,%s,%s)",
                       (wh_id, name, space))
        conn.commit()
        self.warehouses_map[wh_id] = Warehouse(wh_id, name, space)

    # --- STORE ---
    def remove_store(self, store_id, cursor, conn):
        """Xóa kho khỏi DB và RAM — dùng cho Undo AddStore"""
        cursor.execute("DELETE FROM stores WHERE id=%s", (store_id,))
        conn.commit()
        self.stores_map.pop(store_id, None)

    def restore_store(self, store_id, name, location, cursor, conn):
        """Chèn lại cửa hàng — dùng cho Redo AddStore"""
        cursor.execute("INSERT INTO stores (id, name, location) VALUES (%s,%s,%s)",
                       (store_id, name, location))
        conn.commit()
        self.stores_map[store_id] = Store(store_id, name, location)

    def get_kpi_stats(self):
        total_products = len(self.products_map)
        total_warehouses = len(self.warehouses_map)
        total_stores = len(self.stores_map)
        total_value = 0
        for inv in self.inventory_map.values():
            prod = self.products_map.get(inv.product_id)
            if prod:
                try:
                    total_value += inv.quantity * float(prod.price)
                except ValueError:
                    pass
        value_str = f"${total_value/1000:.1f}k" if total_value >= 1000 else f"${total_value:.2f}"
        return {
            "Total Products": {"value": str(total_products), "trend": "↗ +12%"},
            "Warehouses": {"value": str(max(total_warehouses, 1)), "trend": "↗ +1%"},
            "Stores": {"value": str(max(total_stores, 1)), "trend": "↗ +5%"},
            "Inventory Value": {"value": value_str, "trend": "↗ +8%"},
            "Low Stock Count": str(len(self.get_low_stock_items())),
            "Expiring Count": str(len(self.get_expiring_items()))
        }