class Category:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.quantity = 0
    
    def __str__(self):
        return f"Category {self.name}: [ID: {self.id}, Quantity: {self.quantity}]"