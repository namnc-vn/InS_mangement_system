from collections import deque

# ==========================================
# COMMAND PATTERN — Base class
# ==========================================
class Command:
    def undo(self, service, cursor, conn): pass
    def redo(self, service, cursor, conn): pass
    def description(self): return "Unknown"


# ==========================================
# CÁC LỆNH CỤ THỂ
# Nguyên tắc: Command chỉ gọi service.method()
#             Service mới được phép gọi DB trực tiếp
# ==========================================

class AddInventoryCommand(Command):
    """Lệnh thêm lô hàng mới"""
    def __init__(self, item_id, product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id):
        self.item_id = item_id
        self.product_id = product_id
        self.batch_id = batch_id
        self.mfg_date = mfg_date
        self.exp_date = exp_date
        self.quantity = quantity
        self.warehouse_id = warehouse_id

    def undo(self, service, cursor, conn):
        service.remove_inventory_item(self.item_id, cursor, conn)

    def redo(self, service, cursor, conn):
        service.restore_inventory_item(
            self.item_id, self.product_id, self.batch_id,
            self.mfg_date, self.exp_date, self.quantity,
            self.warehouse_id, cursor, conn
        )

    def description(self):
        return f"Thêm kho: {self.product_id} | Lô {self.batch_id} | SL {self.quantity}"


class UpdateInventoryQtyCommand(Command):
    """Lệnh cộng thêm số lượng vào lô hàng đã tồn tại"""
    def __init__(self, item_id, old_qty, added_qty):
        self.item_id = item_id
        self.old_qty = old_qty
        self.added_qty = added_qty

    def undo(self, service, cursor, conn):
        service.update_inventory_quantity(self.item_id, self.old_qty, cursor, conn)

    def redo(self, service, cursor, conn):
        service.update_inventory_quantity(self.item_id, self.old_qty + self.added_qty, cursor, conn)

    def description(self):
        return f"Cập nhật SL lô ID {self.item_id}: {self.old_qty} → {self.old_qty + self.added_qty}"


class AddProductCommand(Command):
    """Lệnh thêm sản phẩm mới"""
    def __init__(self, prod_id, name, category_id, price, status):
        self.prod_id = prod_id
        self.name = name
        self.category_id = category_id
        self.price = price
        self.status = status

    def undo(self, service, cursor, conn):
        service.remove_product(self.prod_id, cursor, conn)

    def redo(self, service, cursor, conn):
        service.restore_product(
            self.prod_id, self.name, self.category_id,
            self.price, self.status, cursor, conn
        )

    def description(self):
        return f"Thêm sản phẩm: {self.name} ({self.prod_id})"


class AddCategoryCommand(Command):
    """Lệnh thêm danh mục mới"""
    def __init__(self, cat_id, name):
        self.cat_id = cat_id
        self.name = name

    def undo(self, service, cursor, conn):
        service.remove_category(self.cat_id, cursor, conn)

    def redo(self, service, cursor, conn):
        service.restore_category(self.cat_id, self.name, cursor, conn)

    def description(self):
        return f"Thêm danh mục: {self.name} ({self.cat_id})"


class AddWarehouseCommand(Command):
    """Lệnh thêm kho mới"""
    def __init__(self, wh_id, name, space):
        self.wh_id = wh_id
        self.name = name
        self.space = space

    def undo(self, service, cursor, conn):
        service.remove_warehouse(self.wh_id, cursor, conn)

    def redo(self, service, cursor, conn):
        service.restore_warehouse(self.wh_id, self.name, self.space, cursor, conn)

    def description(self):
        return f"Thêm kho: {self.name} ({self.wh_id})"

class AddStoreCommand(Command):
    """Lệnh thêm cửa hàng mới"""
    def __init__(self, store_id, name, location):
        self.store_id = store_id
        self.name = name
        self.location = location

    def undo(self, service, cursor, conn):
        service.remove_store(self.store_id, cursor, conn)

    def redo(self, service, cursor, conn):
        service.restore_store(self.store_id, self.name, self.location, cursor, conn)

    def description(self):
        return f"Thêm cửa hàng: {self.name} ({self.store_id})"

class TransferInventoryCommand(Command):
    """Lệnh chuyển kho (split/merge) — Undo: xóa lô ở đích, trả lại lô ở nguồn"""
    def __init__(self, source_item_id, target_item_id, target_store_id, transfer_qty, is_merge=False):
        self.source_item_id = source_item_id
        self.target_item_id = target_item_id
        self.target_store_id = target_store_id
        self.transfer_qty = transfer_qty
        self.is_merge = is_merge

    def undo(self, service, cursor, conn):
        # 1. Khôi phục số lượng ở Warehouse (nguồn)
        source_item = service.inventory_map.get(self.source_item_id)
        if source_item:
            source_item.quantity += self.transfer_qty
            cursor.execute("UPDATE inventory SET quantity = %s WHERE id = %s", (source_item.quantity, self.source_item_id))
        else:
            # Nếu Warehouse lô cũ đã bị xóa (vì transfer toàn bộ), cần Redo việc chèn lại lô cũ... 
            # Tuy nhiên để đơn giản, ta đang giả sử Transfer chỉ cập nhật source. 
            pass # (Sẽ cần tối ưu thêm nếu source_item bị xóa)

        # 2. Xóa hoặc trừ ở Store (đích)
        target_item = service.inventory_map.get(self.target_item_id)
        if target_item:
            target_item.quantity -= self.transfer_qty
            if target_item.quantity > 0:
                cursor.execute("UPDATE inventory SET quantity = %s WHERE id = %s", (target_item.quantity, self.target_item_id))
            else:
                service.remove_inventory_item(self.target_item_id, cursor, conn)
        conn.commit()

    def redo(self, service, cursor, conn):
        service.transfer_inventory(self.source_item_id, self.target_store_id, self.transfer_qty, cursor, conn)

    def description(self):
        return f"Chuyển {self.transfer_qty} sản phẩm sang Cửa hàng {self.target_store_id}"


# ==========================================
# COMMAND HISTORY — 2 Stack (undo + redo)
# ==========================================
class CommandHistory:
    """
    Quản lý lịch sử lệnh theo Command Pattern.
    Dùng 2 Stack (deque) để hỗ trợ Undo / Redo.

    Luồng hoạt động:
        push(cmd)  → undo_stack.append(cmd), redo_stack.clear()
        undo()     → cmd = undo_stack.pop(), cmd.undo(), redo_stack.append(cmd)
        redo()     → cmd = redo_stack.pop(), cmd.redo(), undo_stack.append(cmd)
    """
    MAX_SIZE = 30

    def __init__(self):
        self.undo_stack = deque(maxlen=self.MAX_SIZE)
        self.redo_stack = deque(maxlen=self.MAX_SIZE)

    def push(self, command):
        """Đẩy lệnh mới — xóa redo stack (hành động mới bẻ gãy chuỗi redo)"""
        self.undo_stack.append(command)
        self.redo_stack.clear()

    def undo(self, service, cursor, conn):
        if not self.undo_stack:
            return None
        cmd = self.undo_stack.pop()
        cmd.undo(service, cursor, conn)
        self.redo_stack.append(cmd)
        return cmd

    def redo(self, service, cursor, conn):
        if not self.redo_stack:
            return None
        cmd = self.redo_stack.pop()
        cmd.redo(service, cursor, conn)
        self.undo_stack.append(cmd)
        return cmd

    def can_undo(self): return len(self.undo_stack) > 0
    def can_redo(self): return len(self.redo_stack) > 0

    def peek_undo(self):
        return self.undo_stack[-1].description() if self.undo_stack else None

    def peek_redo(self):
        return self.redo_stack[-1].description() if self.redo_stack else None
