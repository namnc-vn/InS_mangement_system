class Product:
    def __init__(self, id, name, category_id, price, status = "Available"):
        self.id = id
        self.name = name
        self.category_id = category_id
        self.price = price
        self.status = status
    def __str__(self):
        return f"{self.name}: [ID: {self.id}, Price:{self.price}, Category ID: {self.category_id}, Status: {self.status}]"