import random
from datetime import datetime

class InventoryItem:
    def __init__(self, id, product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id = None):
        self.id = id
        self.product_id = product_id
        self.quantity = quantity
        self.batch_id = batch_id
        self.mfg_date = mfg_date
        self.exp_date = exp_date
        self.warehouse_id = warehouse_id
    
    def __str__(self):
        return f"Item {self.id}: Product ID: {self.product_id}, Quantity: {self.quantity}, Batch: {self.batch_id}, MFG: {self.mfg_date}, EXP: {self.exp_date}, Warehouse: {self.warehouse_id}"
    
    def update_quantity(self, quantity):
        self.quantity += quantity