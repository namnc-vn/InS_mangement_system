import heapq
from datetime import datetime, date
from collections import deque

from batch_item import BatchItem
from product import Product
from category import Category
from warehouse import Warehouse
from store import Store
from transfer_task import TransferTask

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

class BatchBST:
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
    def __init__(self, conn=None):
        # --- Database connection ---
        self.conn = conn
        self.cursor = conn.cursor() if conn is not None else None

        # --- Hash Maps (O(1) lookup) ---
        self.categories_map = {}
        self.products_map = {}
        self.batch_map = {}              # Temporary cache: chỉ load khi cần
        self.batch_composite_map = {}   # Composite key → chống trùng lô hàng
        self.warehouses_map = {}
        self.stores_map = {}

        # --- DSA nâng cao ---
        self.qty_bst = BatchBST()           # BST range search (chỉ cho loaded items)
        self.product_id_trie = Trie()           # Autocomplete Product ID
        self.batch_id_trie = Trie()             # Autocomplete Batch ID
        self.product_name_trie = ProductTrie()  # Search sản phẩm theo tên

        # --- Deque: Lịch sử 5 sản phẩm vừa xem (LRU Cache đơn giản) ---
        self.recently_viewed = deque(maxlen=5)

        # --- Lazy Loading Cache ---
        self.loaded_product_batches = {}    # {product_id: [BatchItem]} - cache tạm thời
        self.low_stock_summary = {}             # {product_id: total_quantity} - aggregate
        self.expiring_summary = {}              # {product_id: count_expiring_batches} - aggregate

        # --- Transfer Tasks ---
        self.transfer_tasks = {}               # {task_id: TransferTask}
        self.next_task_id = 1

        self.settings = {
            "low_stock_threshold": 15,
            "expiring_days_threshold": 30,
            "aging_days_threshold": 30
        }

    # =========================================================================
    # TẢI DỮ LIỆU
    # =========================================================================
    def load_data(self):
        """Nạp dữ liệu với lazy loading — chỉ aggregate data để tiết kiệm RAM"""
        if self.cursor is None:
            raise ValueError("Service has no database cursor")

        self.categories_map.clear()
        self.products_map.clear()
        self.batch_map.clear()  # Không load batch items nữa
        self.batch_composite_map.clear()
        self.warehouses_map.clear()
        self.stores_map.clear()
        self.qty_bst = BatchBST()  # Sẽ load on-demand
        self.product_id_trie = Trie()
        self.batch_id_trie = Trie()
        self.product_name_trie = ProductTrie()
        self.loaded_product_batches.clear()
        self.low_stock_summary.clear()
        self.expiring_summary.clear()

        # Load categories
        self.cursor.execute("SELECT * FROM categories")
        for row in self.cursor.fetchall():
            cat = Category(row[0], row[1])
            self.categories_map[cat.id] = cat

        # Load products với aggregate data
        self.cursor.execute("""
            SELECT p.*, 
                   COALESCE(SUM(i.quantity), 0) as total_quantity,
                   CASE WHEN MIN(DATEDIFF(i.exp_date, CURDATE())) <= %s THEN 1 ELSE 0 END as has_expiring,
                   CASE WHEN COALESCE(SUM(i.quantity), 0) <= %s THEN 1 ELSE 0 END as has_low_stock
            FROM products p
            LEFT JOIN batch i ON p.id = i.product_id
            GROUP BY p.id
        """, (self.settings["expiring_days_threshold"], self.settings["low_stock_threshold"]))

        for row in self.cursor.fetchall():
            prod = Product(row[0], row[1], row[2], row[3], row[4], row[5], bool(row[6]), bool(row[7]))
            self.products_map[prod.id] = prod
            self.product_id_trie.insert(prod.id)
            self.product_name_trie.insert(prod.name, prod.id)

            # Lưu aggregate cho warnings
            self.low_stock_summary[prod.id] = prod.total_quantity
            if prod.has_expiring:
                # Đếm số lô sắp hết hạn cho sản phẩm này
                self.cursor.execute("""
                    SELECT COUNT(*) FROM batch 
                    WHERE product_id = %s AND DATEDIFF(exp_date, CURDATE()) <= %s
                """, (prod.id, self.settings["expiring_days_threshold"]))
                self.expiring_summary[prod.id] = self.cursor.fetchone()[0]

        # Load warehouses và stores (không thay đổi)
        try:
            self.cursor.execute("SELECT * FROM warehouses")
            for row in self.cursor.fetchall():
                wh = Warehouse(row[0], row[1], row[2])
                self.warehouses_map[wh.id] = wh
        except Exception:
            pass  # Bảng warehouses chưa tồn tại thì bỏ qua

        try:
            self.cursor.execute("SELECT * FROM stores")
            for row in self.cursor.fetchall():
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

    def batch_id_exists(self, batch_id):
        if batch_id in self.batch_map:
            return True
        if self.cursor is None:
            return False
        self.cursor.execute("SELECT 1 FROM batch WHERE batch_id = %s LIMIT 1", (batch_id,))
        return self.cursor.fetchone() is not None

    def get_unique_batch_id(self, base_batch_id):
        candidate = base_batch_id
        suffix = 1
        while self.batch_id_exists(candidate):
            candidate = f"{base_batch_id}-{suffix}"
            suffix += 1
        return candidate

    # =========================================================================
    # CATEGORY
    # =========================================================================
    def generate_category_id(self):
        return self._get_next_id(self.categories_map, "C")

    def add_category(self, id, name):
        """Thêm danh mục mới — kiểm tra trùng ID bằng Hash Map O(1)"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        if id in self.categories_map:
            return False
        self.cursor.execute("INSERT INTO categories (id, name) VALUES (%s, %s)", (id, name))
        self.conn.commit()
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

    def add_product(self, prod_id, name, category_id, price, status):
        """Thêm sản phẩm mới + cập nhật Trie"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        if prod_id in self.products_map:
            return False
        self.cursor.execute(
            "INSERT INTO products (id, name, category_id, price, status) VALUES (%s, %s, %s, %s, %s)",
            (prod_id, name, category_id, price, status)
        )
        self.conn.commit()
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

    # =========================================================================
    # LAZY LOADING BATCH
    # =========================================================================
    def load_product_batch(self, product_id):
        """Lazy load batch items cho một sản phẩm cụ thể"""
        if self.cursor is None:
            raise ValueError("Service has no database cursor")
        if product_id in self.loaded_product_batches:
            return self.loaded_product_batches[product_id]

        # Query DB để load batch cho product này
        try:
            self.cursor.execute(
                "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id "
                "FROM batch WHERE product_id = %s",
                (product_id,)
            )
        except Exception as e:
            if "Unknown column" in str(e) or "1054" in str(e):
                self.cursor.execute(
                    "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, warehouse_id, store_id "
                    "FROM batch WHERE product_id = %s",
                    (product_id,)
                )
            else:
                raise
        items = []
        for row in self.cursor.fetchall():
            item = self._build_batch_item_from_row(row)
            items.append(item)
            # Thêm vào global batch_map (temporary)
            self.batch_map[item.batch_id] = item
            comp_key = (item.product_id, item.batch_id,
                        str(item.mfg_date), str(item.exp_date), item.warehouse_id, item.store_id)
            self.batch_composite_map[comp_key] = item
            # Thêm vào BST và Trie
            self.qty_bst.insert(item.quantity, item)
            self.batch_id_trie.insert(item.batch_id)

        self.loaded_product_batches[product_id] = items
        return items

    def update_product_aggregates(self, product_id):
        """Cập nhật aggregate data cho một sản phẩm sau khi thay đổi batch"""
        if self.cursor is None:
            raise ValueError("Service has no database cursor")
        self.cursor.execute("""
            SELECT 
                COALESCE(SUM(quantity), 0) as total_quantity,
                CASE WHEN MIN(DATEDIFF(exp_date, CURDATE())) <= %s THEN 1 ELSE 0 END as has_expiring,
                CASE WHEN COALESCE(SUM(quantity), 0) <= %s THEN 1 ELSE 0 END as has_low_stock
            FROM batch 
            WHERE product_id = %s
        """, (self.settings["expiring_days_threshold"], self.settings["low_stock_threshold"], product_id))
        
        row = self.cursor.fetchone()
        if row:
            product = self.products_map.get(product_id)
            if product:
                product.total_quantity = row[0]
                product.has_expiring = bool(row[1])
                product.has_low_stock = bool(row[2])
                
                self.low_stock_summary[product_id] = row[0]
                if bool(row[1]):
                    # Đếm số lô expiring
                    self.cursor.execute("""
                        SELECT COUNT(*) FROM batch 
                        WHERE product_id = %s AND DATEDIFF(exp_date, CURDATE()) <= %s
                    """, (product_id, self.settings["expiring_days_threshold"]))
                    self.expiring_summary[product_id] = self.cursor.fetchone()[0]
                else:
                    self.expiring_summary[product_id] = 0

    def clear_batch_cache(self):
        """Xóa temporary cache để tiết kiệm RAM"""
        self.batch_map.clear()
        self.batch_composite_map.clear()
        self.qty_bst = BatchBST()
        self.batch_id_trie = Trie()
        self.loaded_product_batches.clear()

    def search_products_by_name(self, prefix):
        """Tìm kiếm theo tên bằng ProductTrie — O(L + DFS)"""
        if not prefix.strip():
            return []
        ids = self.product_name_trie.search_prefix(prefix)
        return [self.products_map[pid] for pid in ids if pid in self.products_map]

    def get_recently_viewed_products(self):
        """Lấy lịch sử 5 sản phẩm vừa xem — Deque"""
        return [self.products_map.get(pid) for pid in reversed(self.recently_viewed)]

    def _build_batch_item_from_row(self, row):
        """Xây dựng BatchItem từ row, tương thích cả khi DB chưa có cột unit_price."""
        if len(row) == 9:
            return BatchItem(
                batch_id=row[0], product_id=row[1], mfg_date=row[2], exp_date=row[3],
                entry_date=row[4], quantity=row[5], unit_price=row[6],
                warehouse_id=row[7], store_id=row[8]
            )
        if len(row) == 8:
            return BatchItem(
                batch_id=row[0], product_id=row[1], mfg_date=row[2], exp_date=row[3],
                entry_date=row[4], quantity=row[5], unit_price=0,
                warehouse_id=row[6], store_id=row[7]
            )
        raise ValueError(f"Unexpected batch row shape: {len(row)} columns")

    # =========================================================================
    # BATCH
    # =========================================================================
    def check_batch_exist(self, product_id, batch_id, mfg_date, exp_date, warehouse_id, store_id=None):
        """Kiểm tra lô hàng đã tồn tại bằng Composite Key — O(1) hoặc DB lookup nếu chưa cache"""
        comp_key = (product_id, batch_id, str(mfg_date), str(exp_date), warehouse_id, store_id)
        if comp_key in self.batch_composite_map:
            return self.batch_composite_map[comp_key]
        if self.cursor is None:
            return None
        try:
            self.cursor.execute(
                "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id "
                "FROM batch WHERE product_id=%s AND batch_id=%s AND mfg_date=%s AND exp_date=%s AND warehouse_id=%s AND store_id=%s",
                (product_id, batch_id, mfg_date, exp_date, warehouse_id, store_id)
            )
        except Exception as e:
            if "Unknown column" in str(e) or "1054" in str(e):
                self.cursor.execute(
                    "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, warehouse_id, store_id "
                    "FROM batch WHERE product_id=%s AND batch_id=%s AND mfg_date=%s AND exp_date=%s AND warehouse_id=%s AND store_id=%s",
                    (product_id, batch_id, mfg_date, exp_date, warehouse_id, store_id)
                )
            else:
                raise
        row = self.cursor.fetchone()
        if not row:
            return None
        item = self._build_batch_item_from_row(row)
        self.batch_map[item.batch_id] = item
        self.batch_composite_map[comp_key] = item
        self.batch_id_trie.insert(batch_id)
        return item

    def add_batch_item(self, product_id, quantity, batch_id, mfg_date, exp_date, entry_date, warehouse_id, store_id=None, unit_price=0):
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        existing = self.check_batch_exist(product_id, batch_id, mfg_date, exp_date, warehouse_id, store_id)
        if existing:
            existing.quantity += int(quantity)
            if unit_price is not None and float(unit_price) != float(existing.unit_price):
                existing.unit_price = float(unit_price)
                self.cursor.execute("UPDATE batch SET quantity = %s, unit_price = %s WHERE batch_id = %s",
                                    (existing.quantity, existing.unit_price, existing.batch_id))
            else:
                self.cursor.execute("UPDATE batch SET quantity = %s WHERE batch_id = %s",
                                    (existing.quantity, existing.batch_id))
            self.conn.commit()
            # Cập nhật aggregate data
            self.update_product_aggregates(product_id)
            return True, existing.batch_id
        else:
            insert_batch_id = batch_id
            if self.batch_id_exists(batch_id):
                insert_batch_id = self.get_unique_batch_id(batch_id)

            self.cursor.execute(
                "INSERT INTO batch (batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (insert_batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id)
            )
            self.conn.commit()
            new_item = BatchItem(insert_batch_id, product_id, mfg_date,
                                 exp_date, entry_date, int(quantity), unit_price, warehouse_id, store_id)
            self.batch_map[insert_batch_id] = new_item
            comp_key = (product_id, insert_batch_id, str(mfg_date), str(exp_date), warehouse_id, store_id)
            self.batch_composite_map[comp_key] = new_item
            self.qty_bst.insert(int(quantity), new_item)
            self.batch_id_trie.insert(insert_batch_id)
            # Cập nhật aggregate data
            self.update_product_aggregates(product_id)
            return True, insert_batch_id

    def find_batch_by_product_id(self, product_id):
        if product_id not in self.loaded_product_batches:
            try:
                self.load_product_batch(product_id)
            except ValueError:
                pass
        return self.loaded_product_batches.get(product_id, [])

    def show_batch(self):
        return list(self.batch_map.values())

    # =========================================================================
    # WAREHOUSE
    # =========================================================================
    def generate_warehouse_id(self):
        return self._get_next_id(self.warehouses_map, "WH-")

    def add_warehouse(self, wh_id, name, space):
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        if wh_id in self.warehouses_map:
            return False
        self.cursor.execute("INSERT INTO warehouses (id, name, space) VALUES (%s, %s, %s)",
                       (wh_id, name, space))
        self.conn.commit()
        self.warehouses_map[wh_id] = Warehouse(wh_id, name, space)
        return True

    def get_warehouse_summary(self):
        """Thống kê lô hàng & tổng số lượng theo từng kho — O(n) Hash Map"""
        summary = {}
        for inv in self.batch_map.values():
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

    def add_store(self, store_id, name, location):
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        if store_id in self.stores_map:
            return False
        self.cursor.execute("INSERT INTO stores (id, name, location) VALUES (%s, %s, %s)",
                       (store_id, name, location))
        self.conn.commit()
        self.stores_map[store_id] = Store(store_id, name, location)
        return True

    def get_store_summary(self):
        summary = {}
        for inv in self.batch_map.values():
            if inv.store_id:
                st_id = inv.store_id
                if st_id not in summary:
                    summary[st_id] = {"batches": 0, "total_qty": 0}
                summary[st_id]["batches"] += 1
                summary[st_id]["total_qty"] += inv.quantity
        return summary

    def transfer_batch(self, batch_id, target_location_id, target_location_type, transfer_qty):
        """Chuyển số lượng từ batch nguồn sang warehouse hoặc store đích."""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        if target_location_type not in ("warehouse", "store"):
            raise ValueError("target_location_type phải là 'warehouse' hoặc 'store'")

        source_item = self.batch_map.get(batch_id)
        if not source_item:
            try:
                self.cursor.execute(
                    "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id "
                    "FROM batch WHERE batch_id = %s",
                    (batch_id,)
                )
            except Exception as e:
                if "Unknown column" in str(e) or "1054" in str(e):
                    self.cursor.execute(
                        "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, warehouse_id, store_id "
                        "FROM batch WHERE batch_id = %s",
                        (batch_id,)
                    )
                else:
                    raise
            row = self.cursor.fetchone()
            if not row:
                return False, f"Batch {batch_id} không tồn tại"
            source_item = self._build_batch_item_from_row(row)
            self.batch_map[batch_id] = source_item

        if source_item.quantity < transfer_qty:
            return False, f"Không đủ số lượng. Batch {batch_id} chỉ có {source_item.quantity}, cần {transfer_qty}"

        if target_location_type == "warehouse":
            if source_item.warehouse_id == target_location_id:
                return False, "Source và target warehouse phải khác nhau"
        else:
            if source_item.store_id == target_location_id:
                return False, "Source và target store phải khác nhau"

        source_warehouse_id = source_item.warehouse_id
        source_store_id = source_item.store_id

        source_item.quantity -= transfer_qty
        if source_item.quantity > 0:
            self.cursor.execute("UPDATE batch SET quantity = %s WHERE batch_id = %s", (source_item.quantity, batch_id))
        else:
            self.cursor.execute("DELETE FROM batch WHERE batch_id = %s", (batch_id,))
            self.batch_map.pop(batch_id, None)
            comp_key = (source_item.product_id, source_item.batch_id, str(source_item.mfg_date), str(source_item.exp_date), source_item.warehouse_id, source_item.store_id)
            self.batch_composite_map.pop(comp_key, None)
        self.conn.commit()

        from datetime import date
        entry_date = date.today()
        warehouse_id = target_location_id if target_location_type == "warehouse" else None
        store_id = target_location_id if target_location_type == "store" else None
        _, target_batch_id = self.add_batch_item(
            source_item.product_id, transfer_qty, source_item.batch_id,
            source_item.mfg_date, source_item.exp_date, entry_date,
            warehouse_id, store_id=store_id, unit_price=source_item.unit_price
        )
        return True, target_batch_id

    # =========================================================================
    # ALERTS — Heap-based
    # =========================================================================
    def get_low_stock_warnings(self, threshold=50):
        """Cảnh báo sắp hết hàng — dùng aggregate data O(n log k)"""
        min_heap = []
        for prod_id, total_qty in self.low_stock_summary.items():
            if total_qty <= threshold:
                heapq.heappush(min_heap, (total_qty, prod_id))

        warnings = []
        while min_heap:
            qty, prod_id = heapq.heappop(min_heap)
            product = self.products_map[prod_id]
            warnings.append({"id": product.id, "name": product.name, "total_quantity": qty})
        return warnings

    def get_expiring_soon_warnings(self, days_threshold=30):
        """Cảnh báo sắp hết hạn — lazy load batch cho sản phẩm có expiring"""
        if self.cursor is None:
            return []

        today = date.today()
        min_heap = []

        # Load batch cho các sản phẩm có expiring
        for prod_id, expiring_count in self.expiring_summary.items():
            if expiring_count > 0:
                items = self.load_product_batch(prod_id)
                for item in items:
                    if isinstance(item.exp_date, str):
                        exp_obj = datetime.strptime(item.exp_date, "%Y-%m-%d").date()
                    else:
                        exp_obj = item.exp_date
                    days_left = (exp_obj - today).days
                    if days_left <= days_threshold:
                        heapq.heappush(min_heap, (days_left, item.batch_id, item))

        warnings = []
        while min_heap:
            days_left, _, item = heapq.heappop(min_heap)
            product = self.products_map.get(item.product_id)
            warnings.append({
                "batch_id": item.batch_id,
                "product_name": product.name if product else "Unknown",
                "exp_date": item.exp_date,
                "days_left": days_left,
                "quantity": item.quantity,
                "warehouse_id": item.warehouse_id
            })
        return warnings

    def get_low_stock_items(self):
        """Lấy danh sách lô hàng thấp — lazy load"""
        if self.cursor is None:
            return []
        threshold = self.settings["low_stock_threshold"]
        min_heap = []

        # Load batch cho các sản phẩm có low stock
        for prod_id, total_qty in self.low_stock_summary.items():
            if total_qty <= threshold:
                items = self.load_product_batch(prod_id)
                for inv in items:
                    if inv.quantity <= threshold:
                        heapq.heappush(min_heap, (inv.quantity, inv.batch_id, inv))

        return [heapq.heappop(min_heap)[2] for _ in range(len(min_heap))]

    def get_expiring_items(self):
        """Lấy danh sách lô sắp hết hạn — lazy load"""
        if self.cursor is None:
            return []
        threshold = self.settings["expiring_days_threshold"]
        today = date.today()
        min_heap = []

        # Load batch cho các sản phẩm có expiring
        for prod_id, expiring_count in self.expiring_summary.items():
            if expiring_count > 0:
                items = self.load_product_batch(prod_id)
                for inv in items:
                    try:
                        exp = (datetime.strptime(str(inv.exp_date), "%Y-%m-%d").date()
                               if isinstance(inv.exp_date, str) else inv.exp_date)
                        days_left = (exp - today).days
                        if days_left <= threshold:
                            heapq.heappush(min_heap, (days_left, inv.batch_id, inv))
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
        elif item_type == "Batch":
            if not keyword.strip():
                return list(self.batch_map.values())
            for inv in self.batch_map.values():
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

    # --- BATCH ---
    def remove_batch_item(self, batch_id):
        """Xóa lô hàng khỏi DB và cập nhật RAM — dùng cho Undo AddBatch"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute("DELETE FROM batch WHERE batch_id=%s", (batch_id,))
        self.conn.commit()
        item = self.batch_map.pop(batch_id, None)
        if item:
            comp_key = (item.product_id, item.batch_id,
                        str(item.mfg_date), str(item.exp_date), item.warehouse_id, item.store_id)
            self.batch_composite_map.pop(comp_key, None)
        return item

    def restore_batch_item(self, batch_id, product_id, batch_id_val,
                               mfg_date, exp_date, entry_date, quantity, unit_price=0, warehouse_id=None, store_id=None):
        """Chèn lại lô hàng với batch_id cũ — dùng cho Redo AddBatch"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute(
            "INSERT INTO batch (batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id)
        )
        self.conn.commit()
        new_item = BatchItem(batch_id, product_id, mfg_date,
                                 exp_date, entry_date, quantity, unit_price, warehouse_id, store_id)
        self.batch_map[batch_id] = new_item
        comp_key = (product_id, batch_id_val, str(mfg_date), str(exp_date), warehouse_id, store_id)
        self.batch_composite_map[comp_key] = new_item
        self.qty_bst.insert(quantity, new_item)

    def update_batch_quantity(self, batch_id, new_quantity):
        """Cập nhật số lượng một lô hàng — dùng cho Undo/Redo UpdateQty"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        item = self.batch_map.get(batch_id)
        if item:
            item.quantity = new_quantity
            self.cursor.execute("UPDATE batch SET quantity=%s WHERE batch_id=%s",
                           (new_quantity, batch_id))
            self.conn.commit()
            return True
        return False

    # --- PRODUCT ---
    def remove_product(self, prod_id):
        """Xóa sản phẩm khỏi DB và RAM — dùng cho Undo AddProduct"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute("DELETE FROM products WHERE id=%s", (prod_id,))
        self.conn.commit()
        self.products_map.pop(prod_id, None)

    def restore_product(self, prod_id, name, category_id, price, status):
        """Chèn lại sản phẩm — dùng cho Redo AddProduct"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute(
            "INSERT INTO products (id, name, category_id, price, status) VALUES (%s,%s,%s,%s,%s)",
            (prod_id, name, category_id, price, status)
        )
        self.conn.commit()
        new_prod = Product(prod_id, name, category_id, price, status)
        self.products_map[prod_id] = new_prod
        self.product_id_trie.insert(prod_id)
        self.product_name_trie.insert(name, prod_id)

    # --- CATEGORY ---
    def remove_category(self, cat_id):
        """Xóa danh mục khỏi DB và RAM — dùng cho Undo AddCategory"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute("DELETE FROM categories WHERE id=%s", (cat_id,))
        self.conn.commit()
        self.categories_map.pop(cat_id, None)

    def restore_category(self, cat_id, name):
        """Chèn lại danh mục — dùng cho Redo AddCategory"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute("INSERT INTO categories (id, name) VALUES (%s,%s)", (cat_id, name))
        self.conn.commit()
        self.categories_map[cat_id] = Category(cat_id, name)

    # --- WAREHOUSE ---
    def remove_warehouse(self, wh_id):
        """Xóa kho khỏi DB và RAM — dùng cho Undo AddWarehouse"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute("DELETE FROM warehouses WHERE id=%s", (wh_id,))
        self.conn.commit()
        self.warehouses_map.pop(wh_id, None)

    def restore_warehouse(self, wh_id, name, space):
        """Chèn lại kho — dùng cho Redo AddWarehouse"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute("INSERT INTO warehouses (id, name, space) VALUES (%s,%s,%s)",
                       (wh_id, name, space))
        self.conn.commit()
        self.warehouses_map[wh_id] = Warehouse(wh_id, name, space)

    # --- STORE ---
    def remove_store(self, store_id):
        """Xóa kho khỏi DB và RAM — dùng cho Undo AddStore"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute("DELETE FROM stores WHERE id=%s", (store_id,))
        self.conn.commit()
        self.stores_map.pop(store_id, None)

    def restore_store(self, store_id, name, location):
        """Chèn lại cửa hàng — dùng cho Redo AddStore"""
        if self.cursor is None or self.conn is None:
            raise ValueError("Service has no database connection")
        self.cursor.execute("INSERT INTO stores (id, name, location) VALUES (%s,%s,%s)",
                       (store_id, name, location))
        self.conn.commit()
        self.stores_map[store_id] = Store(store_id, name, location)

    def get_kpi_stats(self):
        total_products = len(self.products_map)
        total_warehouses = len(self.warehouses_map)
        total_stores = len(self.stores_map)
        total_value = 0
        if self.cursor:
            self.cursor.execute(
                "SELECT quantity, COALESCE(unit_price, 0), p.price FROM batch b LEFT JOIN products p ON b.product_id = p.id"
            )
            for qty, unit_price, price in self.cursor.fetchall():
                try:
                    unit_price = float(unit_price or 0)
                except Exception:
                    unit_price = 0
                if unit_price <= 0:
                    try:
                        unit_price = float(price or 0)
                    except Exception:
                        unit_price = 0
                total_value += (qty or 0) * unit_price
        else:
            for inv in self.batch_map.values():
                prod = self.products_map.get(inv.product_id)
                unit_price = float(inv.unit_price or 0)
                if unit_price <= 0 and prod:
                    try:
                        unit_price = float(prod.price or 0)
                    except Exception:
                        unit_price = 0
                total_value += inv.quantity * unit_price

        value_str = f"${total_value/1000:.1f}k" if total_value >= 1000 else f"${total_value:.2f}"
        return {
            "Total Products": {"value": str(total_products), "trend": "↗ +12%"},
            "Warehouses": {"value": str(max(total_warehouses, 1)), "trend": "↗ +1%"},
            "Stores": {"value": str(max(total_stores, 1)), "trend": "↗ +5%"},
            "Batch Value": {"value": value_str, "trend": "↗ +8%"},
            "Low Stock Count": str(len(self.get_low_stock_items())),
            "Expiring Count": str(len(self.get_expiring_items()))
        }

    def _get_batch_inventory_rows(self):
        records = []
        if self.cursor:
            self.cursor.execute(
                "SELECT b.product_id, p.name, b.quantity, COALESCE(b.unit_price, 0), p.price, b.warehouse_id, b.store_id, b.batch_id, b.entry_date, b.exp_date "
                "FROM batch b LEFT JOIN products p ON b.product_id = p.id"
            )
            for row in self.cursor.fetchall():
                records.append(row)
        else:
            for inv in self.batch_map.values():
                prod = self.products_map.get(inv.product_id)
                price = getattr(prod, 'price', 0) if prod else 0
                records.append((inv.product_id, getattr(prod, 'name', inv.product_id), inv.quantity,
                                getattr(inv, 'unit_price', 0), price,
                                inv.warehouse_id, inv.store_id, inv.batch_id, inv.entry_date, inv.exp_date))
        return records

    def get_current_inventory_report(self):
        report = {}
        for product_id, name, qty, unit_price, price, warehouse_id, store_id, batch_id, entry_date, exp_date in self._get_batch_inventory_rows():
            if product_id not in report:
                report[product_id] = {
                    "product_id": product_id,
                    "name": name or product_id,
                    "total_qty": 0,
                    "total_value": 0.0,
                    "warehouse_qty": 0,
                    "store_qty": 0,
                    "batches": 0
                }
            try:
                unit_price = float(unit_price or 0)
            except Exception:
                unit_price = 0
            if unit_price <= 0:
                try:
                    unit_price = float(price or 0)
                except Exception:
                    unit_price = 0
            report[product_id]["total_qty"] += qty or 0
            report[product_id]["total_value"] += (qty or 0) * unit_price
            report[product_id]["warehouse_qty"] += qty or 0 if warehouse_id else 0
            report[product_id]["store_qty"] += qty or 0 if store_id else 0
            report[product_id]["batches"] += 1

        return sorted(report.values(), key=lambda x: x["total_qty"], reverse=True)

    def get_products_with_highest_store_inventory(self, limit=10):
        report = self.get_current_inventory_report()
        stores = [item for item in report if item["store_qty"] > 0]
        return sorted(stores, key=lambda x: x["store_qty"], reverse=True)[:limit]

    def get_aging_inventory(self, min_days=None, limit=20):
        if min_days is None:
            min_days = self.settings["aging_days_threshold"]
        rows = []
        today = date.today()
        for product_id, name, qty, unit_price, price, warehouse_id, store_id, batch_id, entry_date, exp_date in self._get_batch_inventory_rows():
            if not entry_date:
                continue
            try:
                if isinstance(entry_date, str):
                    entry_date_obj = datetime.strptime(entry_date, "%Y-%m-%d").date()
                else:
                    entry_date_obj = entry_date
                days_in_stock = (today - entry_date_obj).days
            except Exception:
                continue
            if days_in_stock >= min_days:
                rows.append({
                    "batch_id": batch_id,
                    "product_id": product_id,
                    "name": name or product_id,
                    "quantity": qty or 0,
                    "entry_date": entry_date_obj,
                    "days_in_stock": days_in_stock,
                    "location": f"🏪 {store_id}" if store_id else f"🏢 {warehouse_id}" if warehouse_id else "Unknown"
                })
        return sorted(rows, key=lambda x: x["days_in_stock"], reverse=True)[:limit]

    def get_inventory_value(self):
        total_value = 0.0
        for product_id, name, qty, unit_price, price, warehouse_id, store_id, batch_id, entry_date, exp_date in self._get_batch_inventory_rows():
            try:
                unit_price = float(unit_price or 0)
            except Exception:
                unit_price = 0
            if unit_price <= 0:
                try:
                    unit_price = float(price or 0)
                except Exception:
                    unit_price = 0
            total_value += (qty or 0) * unit_price
        return total_value

    # =========================================================================
    # TRANSFER TASKS
    # =========================================================================
    def get_warehouse_batches_for_product(self, product_id, sort_strategy="fifo"):
        """Lấy danh sách batch của product từ warehouse, sorted theo chiến lược
        
        sort_strategy:
        - "fifo": expiry_date ASC, entry_date ASC, quantity ASC
        - "lifo": expiry_date DESC, entry_date DESC, quantity DESC  
        - "fefo": expiry_date ASC, entry_date ASC, quantity DESC (ưu tiên hết hạn sớm)
        """
        if self.cursor is None:
            return []
        
        # Load tất cả batch của product từ warehouse
        try:
            self.cursor.execute(
                "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id "
                "FROM batch WHERE product_id = %s AND warehouse_id IS NOT NULL",
                (product_id,)
            )
        except Exception as e:
            if "Unknown column" in str(e) or "1054" in str(e):
                self.cursor.execute(
                    "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, warehouse_id, store_id "
                    "FROM batch WHERE product_id = %s AND warehouse_id IS NOT NULL",
                    (product_id,)
                )
            else:
                raise
        
        batches = []
        for row in self.cursor.fetchall():
            item = self._build_batch_item_from_row(row)
            batches.append(item)
            # Cache batch object so later chuyển task không bị missing
            self.batch_map[item.batch_id] = item
            comp_key = (item.product_id, item.batch_id,
                        str(item.mfg_date), str(item.exp_date), item.warehouse_id, item.store_id)
            self.batch_composite_map[comp_key] = item
        
        # Sort theo chiến lược
        if sort_strategy == "fifo":
            # FIFO: expiry_date ASC, entry_date ASC, quantity ASC
            batches.sort(key=lambda b: (b.exp_date, b.entry_date, b.quantity))
        elif sort_strategy == "lifo":
            # LIFO: expiry_date DESC, entry_date DESC, quantity DESC
            batches.sort(key=lambda b: (b.exp_date, b.entry_date, b.quantity), reverse=True)
        elif sort_strategy == "fefo":
            # FEFO: expiry_date ASC, entry_date ASC, quantity DESC (ưu tiên hết hạn sớm, lấy nhiều nhất)
            batches.sort(key=lambda b: (b.exp_date, b.entry_date, -b.quantity))
        
        return batches

    def get_product_location_ids(self, product_id, location_type):
        items = self.load_product_batch(product_id)
        ids = set()
        for item in items:
            if location_type == "warehouse" and item.warehouse_id:
                ids.add(item.warehouse_id)
            elif location_type == "store" and item.store_id:
                ids.add(item.store_id)
        return sorted(ids)

    def get_product_batches_for_location(self, product_id, location_type, location_id, sort_strategy="fefo"):
        items = self.load_product_batch(product_id)
        if location_type not in ("warehouse", "store"):
            return []
        batches = []
        for item in items:
            if location_type == "warehouse" and item.warehouse_id == location_id:
                batches.append(item)
            elif location_type == "store" and item.store_id == location_id:
                batches.append(item)
        
        if sort_strategy == "fifo":
            batches.sort(key=lambda b: (b.exp_date, b.entry_date, b.quantity))
        elif sort_strategy == "lifo":
            batches.sort(key=lambda b: (b.exp_date, b.entry_date, b.quantity), reverse=True)
        elif sort_strategy == "fefo":
            batches.sort(key=lambda b: (b.exp_date, b.entry_date, -b.quantity))
        return batches

    def create_transfer_task(self, product_id, target_location_id, target_location_type, quantity, priority="normal", strategy="fefo", source_batch_id=None):
        """Tạo task chuyển hàng - hỗ trợ warehouse/store làm đích"""
        if target_location_type not in ("warehouse", "store"):
            raise ValueError("target_location_type phải là 'warehouse' hoặc 'store'")

        if source_batch_id:
            selected_batch = self.batch_map.get(source_batch_id)
            if not selected_batch:
                try:
                    self.cursor.execute(
                        "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price, warehouse_id, store_id "
                        "FROM batch WHERE batch_id = %s",
                        (source_batch_id,)
                    )
                except Exception as e:
                    if "Unknown column" in str(e) or "1054" in str(e):
                        self.cursor.execute(
                            "SELECT batch_id, product_id, mfg_date, exp_date, entry_date, quantity, warehouse_id, store_id "
                            "FROM batch WHERE batch_id = %s",
                            (source_batch_id,)
                        )
                    else:
                        raise
                row = self.cursor.fetchone()
                if not row:
                    raise ValueError(f"Batch {source_batch_id} không tồn tại")
                selected_batch = self._build_batch_item_from_row(row)
                self.batch_map[source_batch_id] = selected_batch

            if selected_batch.product_id != product_id:
                raise ValueError(f"Batch {source_batch_id} không thuộc sản phẩm {product_id}")
        else:
            raise ValueError("source_batch_id là bắt buộc khi tạo task chuyển nội bộ")

        if target_location_type == "warehouse":
            if selected_batch.warehouse_id == target_location_id:
                raise ValueError("Source và target warehouse phải khác nhau")
        else:
            if selected_batch.store_id == target_location_id:
                raise ValueError("Source và target store phải khác nhau")
        
        task_id = f"T{self.next_task_id:03d}"
        self.next_task_id += 1

        task = TransferTask(task_id, product_id, selected_batch.batch_id, target_location_id,
                            target_location_type, quantity, priority, strategy)
        self.transfer_tasks[task_id] = task

        return task

    def execute_transfer_task(self, task_id):
        """Thực hiện transfer task - cho phép retry task failed"""
        task = self.transfer_tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} không tồn tại")
        
        # Cho phép execute task với status "pending" hoặc "failed" (retry)
        if task.status not in ("pending", "failed"):
            raise ValueError(f"Task {task_id} đã được xử lý với trạng thái: {task.status}, không thể execute")
        
        try:
            success, new_batch_id = self.transfer_batch(task.source_batch_id, task.target_location_id, task.target_location_type, task.quantity)
            if success:
                task.complete()
                task.target_batch_id = new_batch_id
                return True
            else:
                raise ValueError(f"Transfer thất bại cho task {task_id}: {new_batch_id}")
        except Exception as e:
            task.status = "failed"
            raise e

    def get_pending_tasks(self):
        """Lấy danh sách tasks đang pending"""
        return [task for task in self.transfer_tasks.values() if task.status == "pending"]

    def suggest_batch_combinations(self, product_id, transfer_qty, source_location_type="warehouse", source_location_id=None, sort_strategy="fefo"):
        """Gợi ý cách kết hợp batch tối ưu.

        Trả về danh sách suggestions theo thứ tự ưu tiên.
        """
        if source_location_type not in ("warehouse", "store"):
            return []
        if source_location_id is None:
            return []

        batches = self.get_product_batches_for_location(product_id, source_location_type, source_location_id, sort_strategy=sort_strategy)
        if not batches or transfer_qty <= 0:
            return []

        suggestions = []
        total_available = sum(batch.quantity for batch in batches)
        if total_available < transfer_qty:
            return []

        # Option 1: Single batch full pick hoặc split từ 1 batch
        first_single = None
        for batch in batches:
            if batch.quantity >= transfer_qty:
                first_single = {
                    'option_type': 'full' if batch.quantity == transfer_qty else 'split',
                    'batches': [
                        {
                            'batch_id': batch.batch_id,
                            'batch_qty': batch.quantity,
                            'take_qty': transfer_qty
                        }
                    ]
                }
                suggestions.append(first_single)
                break

        # Option 2: Multi-batch combine theo thứ tự ưu tiên
        remaining = transfer_qty
        combo = []
        for batch in batches:
            if remaining <= 0:
                break
            qty_to_take = min(batch.quantity, remaining)
            combo.append({
                'batch_id': batch.batch_id,
                'batch_qty': batch.quantity,
                'take_qty': qty_to_take
            })
            remaining -= qty_to_take

        if remaining == 0:
            if not (len(combo) == 1 and first_single and combo[0]['batch_id'] == first_single['batches'][0]['batch_id']
                    and combo[0]['take_qty'] == first_single['batches'][0]['take_qty']):
                option_type = 'merge' if len(combo) > 1 else (
                    'full' if combo[0]['take_qty'] == combo[0]['batch_qty'] else 'split'
                )
                suggestions.append({
                    'option_type': option_type,
                    'batches': combo
                })

        return suggestions

    def get_all_tasks(self):
        """Lấy tất cả tasks"""
        return list(self.transfer_tasks.values())