class Warehouse:
    def __init__(self, id, name, space):
        self.id = id
        self.name = name
        self.space = space
    
    def __str__(self):
        return f"Warehouse {self.name} [ID: {self.id}, Space: {self.space}] "