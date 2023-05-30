import mysql.connector
from decouple import config

mydb = mysql.connector.connect(
    host=config("DB_HOST"),
    user=config("DB_USER"),
    password=config("DB_PASS"),
    database=config("DB_NAME")
)