import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database="ins_db"
    )
    return conn