from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
import os
import json

router = APIRouter()

@router.post("/process")
async def process_file(file: UploadFile = File(...), filters: str = Form(...)):
    try:
        # Read filters JSON string into Python list
        filter_rules = json.loads(filters)

        # Save uploaded file to a temp location
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, file.filename)
        with open(input_path, "wb") as f:
            f.write(await file.read())

        # Load Excel into pandas DataFrame
        df = pd.read_excel(input_path)

        # Define operator functions
        ops = {
            "=": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
        }

        # Apply filters sequentially
        for rule in filter_rules:
            col, op, val = rule["column"], rule["operation"], rule["value"]
            if op not in ops:
                raise HTTPException(status_code=400, detail=f"Unsupported operation: {op}")

            # Try to convert val to numeric if possible
            try:
                val = float(val)
            except:
                pass

            df = df[ops[op](df[col], val)]

        # Save filtered DataFrame to new Excel file
        output_path = os.path.join(temp_dir, "filtered_output.xlsx")
        df.to_excel(output_path, index=False)

        # Return the file for download
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="filtered_output.xlsx"
        )

    except Exception as e:
        print(f"❌ Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
