import pandas as pd
import os

# Ask user for Excel file path
file_path = input("Enter the full path to your Excel file: ")

# Load file
try:
    df = pd.read_excel(file_path)
except Exception as e:
    print(f"❌ Error loading file: {e}")
    exit()

# Show column names
print("\nAvailable columns:")
print(df.columns.tolist())

# Ask how many filters to apply
num_filters = int(input("\nHow many filters would you like to apply? "))

filters = []
for i in range(num_filters):
    print(f"\nFilter #{i + 1}")
    column = input("Column name: ")
    operation = input("Operation (=, !=, >, <, >=, <=): ")
    value = input("Value: ")

    try:
        value = float(value)
    except:
        pass

    filters.append({
        "column": column,
        "operation": operation,
        "value": value
    })

# Apply filters using operator functions
ops = {
    "=": lambda x, y: x == y,
    "!=": lambda x, y: x != y,
    ">": lambda x, y: x > y,
    "<": lambda x, y: x < y,
    ">=": lambda x, y: x >= y,
    "<=": lambda x, y: x <= y,
}

for rule in filters:
    col, op, val = rule["column"], rule["operation"], rule["value"]
    if op not in ops:
        print(f"⚠️ Unsupported operation: {op}")
        continue
    df = df[ops[op](df[col], val)]

# Save result to Desktop
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
output_path = os.path.join(desktop, "filtered_test_output.xlsx")
df.to_excel(output_path, index=False)

print(f"\n✅ Filtered file saved to: {output_path}")
