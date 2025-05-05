import sqlite3
import os
import pandas as pd

PATH = os.path.dirname(os.path.abspath(__file__))
data = pd.read_excel(f"{PATH}\\tov.xlsx")

keys = [key for key in data]

 
conn = sqlite3.connect(f"{PATH}\\base.db")
cur = conn.cursor()


for string in zip(data[keys[0]], data[keys[1]], data[keys[2]]):
    cur.execute("INSERT INTO base_volt (name, article, vendor) VALUES (?, ?, ?)", string)

conn.commit()
conn.close()