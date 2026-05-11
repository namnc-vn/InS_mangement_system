"""Product domain model used throughout the InS warehouse system."""

class Product:
    """Represents a product item with pricing and inventory alert flags."""
    def __init__(self, id, name, category_id, price, status="Available", total_quantity=0, has_expiring=False, has_low_stock=False):
        self.id = id
        self.name = name
        self.category_id = category_id
        self.price = price
        self.status = status
        # Aggregate data for lazy loading
        self.total_quantity = total_quantity  # Tổng tồn kho từ tất cả lô
        self.has_expiring = has_expiring      # Có lô sắp hết hạn không
        self.has_low_stock = has_low_stock    # Có lô sắp hết hàng không
    def __str__(self):
        alerts = []
        if self.has_low_stock:
            alerts.append("LOW STOCK")
        if self.has_expiring:
            alerts.append("EXPIRING")
        alert_str = f" ({', '.join(alerts)})" if alerts else ""
        return f"{self.name}: [ID: {self.id}, Price:{self.price}, Total Qty:{self.total_quantity}, Category ID: {self.category_id}, Status: {self.status}]{alert_str}"