# Placeholder for database connection
# In a real scenario, this would use SQLAlchemy or similar

class Database:
    def __init__(self):
        self.connected = False

    def connect(self):
        self.connected = True
        print("Connected to database (Mock)")

    def disconnect(self):
        self.connected = False
        print("Disconnected from database (Mock)")

db = Database()
