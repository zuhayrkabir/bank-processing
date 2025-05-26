from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
import json
import os

router = APIRouter()

@router.post("/process")
async def process_file(file: UploadFile = File(...), filters: str = Form(...)):
    try:
        print(f"📥 Received: {file.filename}")
        print(f"📂 File type: {file.filename.split('.')[-1]}")
        print(f"🔍 Filters: {filters}")

        if not file.filename.endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Read the Excel file
        df = pd.read_excel(temp_file_path)

        # Parse filters JSON
        filters_data = json.loads(filters)

        # Apply filters
        for rule in filters_data:
            col = rule["column"]
            op = rule["operation"]
            val = rule["value"]

            # Convert numeric strings to float/int when possible
            try:
                val = eval(val)
            except:
                pass  # Keep as string if eval fails

            if op == "=":
                df = df[df[col] == val]
            elif op == "!=":
                df = df[df[col] != val]
            elif op == ">":
                df = df[df[col] > val]
            elif op == "<":
                df = df[df[col] < val]
            elif op == ">=":
                df = df[df[col] >= val]
            elif op == "<=":
                df = df[df[col] <= val]
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported operation: {op}")

        # Save filtered data to Excel
        output_path = tempfile.mktemp(suffix=".xlsx")
        df.to_excel(output_path, index=False)
        print(f"✅ Filtered file saved to: {output_path}")

        return FileResponse(output_path, filename="filtered_output.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
