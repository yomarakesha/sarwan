import pandas as pd

try:
    df = pd.read_excel('2.02.2026.xlsx', header=None)
    print("Row 17 (Header candidate):")
    print(df.iloc[17].tolist())
except Exception as e:
    print(f"Error reading excel: {e}")
