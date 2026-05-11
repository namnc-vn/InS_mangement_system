"""Transfer task model used for warehouse/store movement workflows."""

from datetime import datetime

class TransferTask:
    """Represents an asynchronous transfer task in the inventory workflow."""
    def __init__(self, task_id, product_id, source_batch_id, target_location_id, target_location_type="store", quantity=0, priority="normal", strategy="fefo"):
        self.task_id = task_id
        self.product_id = product_id
        self.source_batch_id = source_batch_id
        self.target_location_id = target_location_id
        self.target_location_type = target_location_type
        self.quantity = quantity
        self.priority = priority
        self.strategy = strategy
        self.status = "pending"
        self.created_at = datetime.now()
        self.completed_at = None

    def __str__(self):
        return f"Task {self.task_id}: Transfer {self.quantity} of {self.product_id} from {self.source_batch_id} to {self.target_location_type} {self.target_location_id} ({self.status})"

    def start(self):
        self.status = "in_progress"

    def complete(self):
        self.status = "completed"
        self.completed_at = datetime.now()

    def cancel(self):
        self.status = "cancelled"