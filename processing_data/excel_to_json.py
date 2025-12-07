import pandas as pd
import json

data = pd.read_excel("student.xlsx", sheet_name="suraj1")
json_data = data.to_json()
