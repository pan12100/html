import json

with open("credentials.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# แปลงเป็น string บรรทัดเดียว
creds_str = json.dumps(data)

print("\n=== COPY STRING นี้ไปใส่ใน Environment Variable GOOGLE_CREDS ===\n")
print(creds_str)
