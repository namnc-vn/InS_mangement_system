"""Database connection helper for the InS warehouse system."""

import mysql.connector

def get_connection():
    """Return a MySQL connection to the ins_db database."""
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database="ins_db"
    )
    return conn