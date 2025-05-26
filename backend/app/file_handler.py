async def process_file(file, filters: list):
    import pandas as pd
    import os
    import tempfile

    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, file.filename)

    with open(input_path, "wb") as f:
        f.write(await file.read())

    df = pd.read_excel(input_path)

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
        try:
            val = float(val)
        except:
            pass
        if op in ops:
            df = df[ops[op](df[col], val)]

    output_path = os.path.join(temp_dir, "filtered_file.xlsx")
    df.to_excel(output_path, index=False)
    return output_path
