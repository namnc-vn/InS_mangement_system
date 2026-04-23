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
