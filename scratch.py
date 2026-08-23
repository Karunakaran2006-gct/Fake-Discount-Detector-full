import pandas as pd
import io
from fdd.features import extract_features
from fdd.detection import analyze

csv_data = """date,product_name,price
2026-02-16,Nike Air Max,8031
2026-08-08,Nike Air Max,8048
2026-08-09,Nike Air Max,8026
2026-08-10,Nike Air Max,4999
2026-08-11,Nike Air Max,4999
2026-08-12,Nike Air Max,4999
2026-08-13,Nike Air Max,4999
2026-08-14,Nike Air Max,4999
"""
df = pd.read_csv(io.StringIO(csv_data))
df['date'] = pd.to_datetime(df['date'])

features = extract_features(
    df, 
    claimed_original_price=8050.00, 
    claimed_sale_price=4999.00, 
    sale_date="2026-08-14", 
    product_id="Nike Air Max"
)
result = analyze(features)
print(f"Days held: {features.days_original_price_held}")
print(f"Status: {result.status}")
print(f"Score: {result.suspicion_score}")
