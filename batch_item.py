import random
from datetime import datetime

class BatchItem:
    def __init__(self, batch_id, product_id, mfg_date, exp_date, entry_date, quantity, unit_price=0, warehouse_id=None, store_id=None):
        self.batch_id = batch_id
        self.product_id = product_id
        self.quantity = quantity
        self.mfg_date = mfg_date
        self.exp_date = exp_date
        self.entry_date = entry_date
        self.unit_price = unit_price
        self.warehouse_id = warehouse_id
        self.store_id = store_id

    def __str__(self):
        loc = f"Store: {self.store_id}" if self.store_id else f"Warehouse: {self.warehouse_id}"
        return f"Batch {self.batch_id}: Product ID: {self.product_id}, Quantity: {self.quantity}, Unit Price: {self.unit_price}, MFG: {self.mfg_date}, EXP: {self.exp_date}, Entry: {self.entry_date}, {loc}"

    def update_quantity(self, quantity):
        self.quantity += quantity