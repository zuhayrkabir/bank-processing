from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import pandas as pd
import os
import tempfile
import io
import json
import re
import openpyxl
from datetime import datetime
from typing import Dict

router = APIRouter()


# ========= FILTERING FOR EXCEL ROUTE =========

def apply_filters(df, filters):
    ops = {
        "=": lambda col, val: col == val,
        "!=": lambda col, val: col != val,
        ">": lambda col, val: col > val,
        "<": lambda col, val: col < val,
        ">=": lambda col, val: col >= val,
        "<=": lambda col, val: col <= val,
        "contains": lambda col, val: col.astype(str).str.contains(str(val), case=False, na=False),
        "not_contains": lambda col, val: ~col.astype(str).str.contains(str(val), case=False, na=False),
    }

    for rule in filters:
        col = rule.get("column")
        op = rule.get("operation")
        val = rule.get("value")

        if not all([col, op, val]):
            continue

        if op not in ops:
            raise ValueError(f"Unsupported operation: {op}")

        if col not in df.columns:
            raise ValueError(f"Column '{col}' does not exist")

        try:
            if pd.api.types.is_numeric_dtype(df[col]):
                val = float(val)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                val = pd.to_datetime(val)
        except (ValueError, TypeError):
            pass

        df = df[ops[op](df[col], val)]

    return df


@router.post("/convert-txt")
async def convert_txt_to_excel(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        decoded = contents.decode("utf-8")
        df = pd.read_csv(io.StringIO(decoded), sep=r'\s{2,}', engine='python')

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            output_path = tmp.name
            df.to_excel(output_path, index=False)

        return FileResponse(output_path, filename="converted_file.xlsx")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert TXT to Excel.")


@router.post("/process-excel")
async def process_excel_file(file: UploadFile = File(...), filters: str = Form("[]")):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        filter_rules = json.loads(filters)
        if filter_rules:
            df = apply_filters(df, filter_rules)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            output_path = tmp.name
            df.to_excel(output_path, index=False)

        return FileResponse(output_path, filename=f"processed_{file.filename}")

    except Exception as e:
        raise HTTPException(500, f"Failed to process Excel file: {str(e)}")


# ========= VISA REPORT PARSING ROUTE =========
def parse_visa_report(content: str) -> Dict:
    data = {
        'ReportID': '',
        'ReportingFor': '',
        'RollupTo': '',
        'FundsXferEntity': '',
        'ProcDate': '',
        'ReportDate': '',
        'SettlementCurrency': '',
    }

    def parse_amount(amount_str):
        if not amount_str or str(amount_str).strip() in ('', '0.00'):
            return 0.0
        amount_str = str(amount_str).replace(',', '').strip()
        if 'CR' in amount_str:
            return float(amount_str.replace('CR', ''))
        elif 'DB' in amount_str:
            return -float(amount_str.replace('DB', ''))
        try:
            return float(amount_str)
        except ValueError:
            return 0.0 # Return 0.0 if parsing fails


    # Parse headers (unchanged)
    headers = {
        'ReportID': r'REPORT ID:\s+(VSS-\d+)',
        'ReportingFor': r'REPORTING FOR:\s+(.+?)\s+PROC',
        'RollupTo': r'ROLLUP TO:\s+(.+?)\s+SETTLEMENT',
        'FundsXferEntity': r'FUNDS XFER ENTITY:\s+(.+?)\n',
        'ProcDate': r'PROC DATE:\s+(\d{2}[A-Za-z]{3}\d{2})',
        'ReportDate': r'REPORT DATE:\s+(\d{2}[A-Za-z]{3}\d{2})',
        'SettlementCurrency': r'SETTLEMENT CURRENCY:\s+([A-Z]{3})'
    }

    for field, pattern in headers.items():
        if match := re.search(pattern, content):
            data[field] = match.group(1).strip()

    # Define section-specific column parsing logic
    sections = [
        {
            'name': 'Interchange',
            'pattern': r'INTERCHANGE VALUE(.*?)REIMBURSEMENT FEES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'columns': ['Count', 'CreditAmount', 'DebitAmount', 'TotalAmount'],
            'total_pattern': r'TOTAL INTERCHANGE VALUE\s+([\d,]+)\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?'
        },
        {
            'name': 'Reimbursement',
            'pattern': r'REIMBURSEMENT FEES(.*?)VISA CHARGES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'columns': ['CreditAmount', 'DebitAmount', 'TotalAmount'],
            'total_pattern': r'TOTAL REIMBURSEMENT FEES\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?'
        },
        {
            'name': 'VisaCharges',
            'pattern': r'VISA CHARGES(.*?)TOTAL VISA CHARGES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'columns': ['CreditAmount', 'DebitAmount', 'TotalAmount'],
            'total_pattern': r'TOTAL VISA CHARGES\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?'
        }
    ]

    for section in sections:
        print(f"\n🔍 Parsing section: {section['name']}")
        if section_match := re.search(section['pattern'], content, re.DOTALL):
            section_content = section_match.group(1)

            for line_type in section['line_types']:
                print(f"  ➤ Looking for line: TOTAL {line_type} in {section['name']}")

                if section['name'] == 'Interchange':
                    pattern = rf'TOTAL {line_type}\s+(\d+)\s+([\d,]+\.\d{{2}}(?:CR|DB)?)?\s+([\d,]+\.\d{{2}}(?:CR|DB)?)?\s+([\d,]+\.\d{{2}}(?:CR|DB)?)?'
                else:
                    pattern = rf'TOTAL {line_type}\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?'

                if match := re.search(pattern, section_content):
                    print(f"    ✅ Match found: {match.groups()}")

                    start_idx = 1
                    if section['name'] == 'Interchange':
                        count_val = match.group(start_idx)
                        data[f"{section['name']}_{line_type}_Count"] = int(count_val) if count_val else 0
                        print(f"    ↪ Count: {data[f'{section['name']}_{line_type}_Count']}")
                        start_idx += 1

                    credit = match.group(start_idx)
                    debit = match.group(start_idx + 1)
                    total = match.group(start_idx + 2)

                    data[f"{section['name']}_{line_type}_CreditAmount"] = parse_amount(credit)
                    data[f"{section['name']}_{line_type}_DebitAmount"] = parse_amount(debit)
                    data[f"{section['name']}_{line_type}_TotalAmount"] = parse_amount(total)

                    print(f"    ↪ Credit: {credit} ➜ {data[f'{section['name']}_{line_type}_CreditAmount']}")
                    print(f"    ↪ Debit:  {debit} ➜ {data[f'{section['name']}_{line_type}_DebitAmount']}")
                    print(f"    ↪ Total:  {total} ➜ {data[f'{section['name']}_{line_type}_TotalAmount']}")
                else:
                    print(f"    ❌ No match for TOTAL {line_type} in {section['name']}")

            # Parse section total
            print(f"  ➤ Looking for section TOTAL in {section['name']}")
            if total_match := re.search(section['total_pattern'], content):
                print(f"    ✅ Section total match: {total_match.groups()}")

                start_idx = 1
                if section['name'] == 'Interchange':
                    count_val = total_match.group(start_idx)
                    data[f"{section['name']}_Total_Count"] = int(count_val) if count_val else 0
                    print(f"    ↪ Total Count: {data[f'{section['name']}_Total_Count']}")
                    start_idx += 1

                data[f"{section['name']}_Total_CreditAmount"] = parse_amount(total_match.group(start_idx))
                data[f"{section['name']}_Total_DebitAmount"] = parse_amount(total_match.group(start_idx + 1))
                data[f"{section['name']}_Total_TotalAmount"] = parse_amount(total_match.group(start_idx + 2))

                print(f"    ↪ Section Credit: {data[f'{section['name']}_Total_CreditAmount']}")
                print(f"    ↪ Section Debit:  {data[f'{section['name']}_Total_DebitAmount']}")
                print(f"    ↪ Section Total:  {data[f'{section['name']}_Total_TotalAmount']}")
            else:
                print(f"    ❌ No total match for {section['name']}")

    # Parse settlement section
    print("\n🔍 Parsing Settlement Section")
    if settlement_block_match := re.search(r'(TOTAL\s+(?:ACQUIRER|ISSUER|OTHER).*?)(END OF)', content, re.DOTALL):
        settlement_block_content = settlement_block_match.group(1)

        for line_type in ['ACQUIRER', 'ISSUER', 'OTHER']:
            pattern = rf'TOTAL {line_type}\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?'
            if match := re.search(pattern, settlement_block_content):
                print(f"  ✅ Settlement {line_type}: {match.groups()}")
                data[f'Settlement_Total{line_type}_CreditAmount'] = parse_amount(match.group(1))
                data[f'Settlement_Total{line_type}_DebitAmount'] = parse_amount(match.group(2))
                data[f'Settlement_Total{line_type}_TotalAmount'] = parse_amount(match.group(3))
            else:
                print(f"  ❌ No match for TOTAL {line_type} in Settlement")

    if net_match := re.search(r'NET SETTLEMENT AMOUNT\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?', content):
        print(f"  ✅ Matched Net Settlement: {net_match.groups()}")
        data['Settlement_Net_CreditAmount'] = parse_amount(net_match.group(1))
        data['Settlement_Net_DebitAmount'] = parse_amount(net_match.group(2))
        data['Settlement_Net_TotalAmount'] = parse_amount(net_match.group(3))
    else:
        print("  ❌ No match for NET SETTLEMENT AMOUNT")


    print("Dictionary", data)
    return data




def transform_report_data_to_rows(data: dict) -> pd.DataFrame:
    metadata_cols = ['ReportID', 'ReportingFor', 'RollupTo', 'FundsXferEntity', 
                   'ProcDate', 'ReportDate', 'SettlementCurrency']
    
    sections = [
        {
            'MajorType': 'Interchange',
            'MinorTypes': ['ACQUIRER', 'ISSUER', 'OTHER', 'Total'],
            'Fields': ['Count', 'CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'Reimbursement',
            'MinorTypes': ['ACQUIRER', 'ISSUER', 'OTHER', 'Total'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'VisaCharges',
            'MinorTypes': ['ACQUIRER', 'ISSUER', 'OTHER', 'Total'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'Settlement',
            'MinorTypes': ['ACQUIRER', 'ISSUER', 'OTHER', 'Net'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        }
    ]
    
    rows = []
    
    for section in sections:
        for minor_type in section['MinorTypes']:
            row = {col: data.get(col, '') for col in metadata_cols}
            row['MajorType'] = section['MajorType']
            if(section['MajorType'] == 'Settlement'):
                row['MajorType'] = 'Total'
            row['MinorType'] = minor_type
            if(minor_type == 'Net'):
                row['MinorType'] = "Net Settlement Amount"
            
            for field in section['Fields']:
                # Construct the key based on the actual parsing output
                if minor_type == 'Net':
                    key = f"Settlement_Net_{field}"
                elif minor_type == 'Total':
                    key = f"{section['MajorType']}_Total_{field}"
                else:
                    # Match the exact case used in parsing (ACQUIRER, ISSUER, OTHER)
                    key = f"{section['MajorType']}_{minor_type}_{field}"
                
                # Get value with proper fallback
                value = data.get(key)
                
                # Convert to appropriate type
                if value is None:
                    row[field] = 0.0 if 'Amount' in field else 0
                elif isinstance(value, (int, float)):
                    row[field] = value
                else:
                    try:
                        row[field] = float(value) if 'Amount' in field else int(value)
                    except (ValueError, TypeError):
                        row[field] = 0.0 if 'Amount' in field else 0
            
            rows.append(row)
    
    df = pd.DataFrame(rows)
    column_order = metadata_cols + ['MajorType', 'MinorType', 'Count', 
                                 'CreditAmount', 'DebitAmount', 'TotalAmount']
    
    # Convert amount columns to numeric, handling missing values
    amount_cols = ['CreditAmount', 'DebitAmount', 'TotalAmount']
    for col in amount_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    # Fill Count NaN with 0
    if 'Count' in df.columns:
        df['Count'] = df['Count'].fillna(0).astype(int)

    df['TotalType'] = df['TotalAmount'].apply(lambda x: 'CR' if x >= 0 else 'DB')
    df['TotalAmount'] = df['TotalAmount'].abs()
    column_order = metadata_cols + ['MajorType', 'MinorType', 'Count', 
                                'CreditAmount', 'DebitAmount', 'TotalAmount', 'TotalType']
    
    return df[column_order]



def process_multiple_visa_reports(content: str) -> pd.DataFrame:
    # Split content into multiple reports
    reports = content.strip().split("*** END OF VSS-110 REPORT ***")

    final_rows = []

    for idx, report_text in enumerate(reports):
        report_text = report_text.strip()
        if not report_text:
            continue

        print(f"\n📄 Processing Report #{idx+1}...")

        try:
            parsed = parse_visa_report(report_text)
            df = transform_report_data_to_rows(parsed)
            final_rows.append(df)
        except Exception as e:
            print(f"⚠️ Failed to process report #{idx+1}: {e}")

    combined_df = pd.concat(final_rows, ignore_index=True)
    return combined_df



def autosize_excel_columns(filename):
    wb = openpyxl.load_workbook(filename)
    ws = wb.active

    for column_cells in ws.columns:
        max_length = 0
        col_letter = openpyxl.utils.get_column_letter(column_cells[0].column)
        for cell in column_cells:
            if cell.value:
                cell_len = len(str(cell.value))
                if cell_len > max_length:
                    max_length = cell_len
        adjusted_width = (max_length + 2)
        ws.column_dimensions[col_letter].width = adjusted_width

    wb.save(filename)


from fastapi.responses import StreamingResponse
import mimetypes

@router.post("/process-visa-report")
async def process_visa_report(file: UploadFile = File(...)):
    contents = await file.read()
    content_str = contents.decode("utf-8")

    df = process_multiple_visa_reports(content_str)

    # Extract values from second row
    if len(df) > 1:
        second_row = df.iloc[1]
        report_id = str(second_row.get('ReportID', 'VSS-000')).replace("/", "-")
        proc_date = str(second_row.get('ProcDate', 'nodate')).replace("/", "-")
        report_date = str(second_row.get('ReportDate', 'nodate')).replace("/", "-")
        filename = f"{report_id}.{proc_date}.{report_date}.xlsx"
    else:
        filename = "visa_report.xlsx"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        output_path = tmp.name
        df.to_excel(output_path, index=False)
        autosize_excel_columns(output_path)

    file_stream = open(output_path, "rb")
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

