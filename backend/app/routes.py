from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import pandas as pd
import tempfile
import os
import io

router = APIRouter()

def apply_filters(df, filters):
    ops = {
        "=": lambda col, val: col == val,
        "!=": lambda col, val: col != val,
        ">": lambda col, val: col > val,
        "<": lambda col, val: col < val,
        ">=": lambda col, val: col >= val,
        "<=": lambda col, val: col <= val,
        "contains": lambda col, val: col.str.contains(val, case=False, na=False),
        "not_contains": lambda col, val: ~col.str.contains(val, case=False, na=False),
    }

    for rule in filters:
        col = rule["column"]
        op = rule["operation"]
        val = rule["value"]

        if op not in ops:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {op}")

        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{col}' does not exist")

        # Apply filter
        df = df[ops[op](df[col].astype(str), val)]

    return df

@router.post("/process")
async def process_file(
    file: UploadFile = File(...),
    filters: str = Form(None),
    filetype: str = Form(...)
):
    print(f"📥 Received file: {file.filename}")
    print(f"📂 File type: {filetype}")
    if filters:
        print(f"🔍 Filters: {filters}")

    # Read file contents into pandas dataframe
    try:
        contents = await file.read()
        if filetype == "xlsx":
            df = pd.read_excel(io.BytesIO(contents))
            if filters:
                import json
                filter_rules = json.loads(filters)
                df = apply_filters(df, filter_rules)
        elif filetype == "txt":
            # Simple assumption: txt file is tab or comma separated, try both
            try:
                df = pd.read_csv(io.BytesIO(contents), delimiter="\t")
            except:
                df = pd.read_csv(io.BytesIO(contents), delimiter=",")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Save output to temp file
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "processed_file.xlsx")
        df.to_excel(output_path, index=False)
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Return file as response
    from fastapi.responses import FileResponse
    return FileResponse(output_path, filename="processed_file.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
