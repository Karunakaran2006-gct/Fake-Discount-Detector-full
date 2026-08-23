import pandas as pd
import io

csv_data = """date,product_name,price
2026-02-16,Nike Air Max,8031
2026-08-09,Nike Air Max,8026
2026-08-10,Nike Air Max,4999
2026-08-11,Nike Air Max,4999
2026-08-14,Nike Air Max,4999
"""

upload_df = pd.read_csv(io.StringIO(csv_data))
prod_df = upload_df[upload_df["product_name"] == "Nike Air Max"].copy()
prod_df["date"] = pd.to_datetime(prod_df["date"])
prod_df = prod_df.sort_values("date")

default_sale = float(prod_df["price"].iloc[-1])
print(f"default_sale: {default_sale}")

sale_rows = prod_df[prod_df["price"] == default_sale]
print(f"sale_rows empty? {sale_rows.empty}")
if not sale_rows.empty:
    default_date = sale_rows["date"].iloc[0].date()
    print(f"Detected default_date: {default_date}")
else:
    print("Fallback to last date")
