class Store:
    def __init__(self, id, name, location):
        self.id = id
        self.name = name
        self.location = location
    
    def __str__(self):
        return f"Store {self.name} [ID: {self.id}, Location: {self.location}] "
