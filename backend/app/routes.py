from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import pandas as pd
import os
import tempfile
import io
import json
import re
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

    # Helper functions
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, '%d%b%y').strftime('%Y-%m-%d')
        except:
            return date_str

    def parse_amount(amount_str):
        if not amount_str:
            return ''
        amount_str = amount_str.replace(',', '').replace('DB', '').replace('CR', '').strip()
        try:
            return float(amount_str)
        except:
            return amount_str

    # Parse header information
    header_patterns = {
        'ReportID': r'REPORT ID:\s+(VSS-\d+)',
        'ReportingFor': r'REPORTING FOR:\s+(.+?)\s+BIN',
        'RollupTo': r'ROLLUP TO:\s+(.+?)\s+BA',
        'FundsXferEntity': r'FUNDS XFER ENTITY:\s+(.+?)\n',
        'ProcDate': r'PROC DATE:\s+(\d{2}[A-Za-z]{3}\d{2})',
        'ReportDate': r'REPORT DATE:\s+(\d{2}[A-Za-z]{3}\d{2})',
        'SettlementCurrency': r'SETTLEMENT CURRENCY:\s+([A-Z]{3})'
    }

    for field, pattern in header_patterns.items():
        match = re.search(pattern, content)
        if match:
            value = match.group(1).strip()
            if 'Date' in field:
                data[field] = parse_date(value)
            else:
                data[field] = value

    # Improved section parser that handles all sections consistently
    def parse_section(section_name, has_count=True):
        # Find the entire section content
        section_pattern = rf'{section_name.upper()}(.*?)(?:TOTAL {section_name.upper()}|TOTAL$)'
        section_match = re.search(section_pattern, content, re.DOTALL)
        if not section_match:
            return
            
        section_content = section_match.group(1)
        
        # Define patterns for each line type
        line_types = ['ACQUIRER', 'ISSUER', 'OTHER']
        
        for line_type in line_types:
            pattern = rf'TOTAL {line_type}\s+({r"(\d+)\s+" if has_count else ""})\s*([\d,]+\.\d{{2}})?\s*([\d,]+\.\d{{2}})?\s*([\d,]+\.\d{{2}}[A-Z]{{2}}?)?'
            match = re.search(pattern, section_content)
            if match:
                groups = match.groups()
                idx = 0
                if has_count:
                    data[f'{section_name}_Total{line_type.capitalize()}_Count'] = groups[idx] if groups[idx] else ''
                    idx += 1
                data[f'{section_name}_Total{line_type.capitalize()}_CreditAmount'] = parse_amount(groups[idx]) if groups[idx] else ''
                data[f'{section_name}_Total{line_type.capitalize()}_DebitAmount'] = parse_amount(groups[idx+1]) if groups[idx+1] else ''
                data[f'{section_name}_Total{line_type.capitalize()}_TotalAmount'] = parse_amount(groups[idx+2]) if groups[idx+2] else ''
        
        # Parse section total
        total_pattern = rf'TOTAL {section_name.upper()} (?:VALUE|FEES|CHARGES)\s+({r"(\d+)\s+" if has_count else ""})\s*([\d,]+\.\d{{2}})?\s*([\d,]+\.\d{{2}})?\s*([\d,]+\.\d{{2}}[A-Z]{{2}}?)?'
        total_match = re.search(total_pattern, content)
        if total_match:
            groups = total_match.groups()
            idx = 0
            if has_count:
                data[f'{section_name}_Total_Count'] = groups[idx] if groups[idx] else ''
                idx += 1
            data[f'{section_name}_Total_CreditAmount'] = parse_amount(groups[idx]) if groups[idx] else ''
            data[f'{section_name}_Total_DebitAmount'] = parse_amount(groups[idx+1]) if groups[idx+1] else ''
            data[f'{section_name}_Total_TotalAmount'] = parse_amount(groups[idx+2]) if groups[idx+2] else ''

    # Parse all sections
    parse_section('Interchange', has_count=True)
    parse_section('Reimbursement', has_count=False)
    parse_section('VisaCharges', has_count=False)
    
    # Parse Settlement section
    settlement_match = re.search(r'TOTAL(.*?)NET SETTLEMENT AMOUNT', content, re.DOTALL)
    if settlement_match:
        settlement_content = settlement_match.group(1)
        
        # Parse Acquirer, Issuer, Other in Settlement
        for entry_type in ['ACQUIRER', 'ISSUER', 'OTHER']:
            pattern = rf'TOTAL {entry_type}\s+([\d,]+\.\d{{2}})?\s*([\d,]+\.\d{{2}})?\s*([\d,]+\.\d{{2}}[A-Z]{{2}}?)?'
            match = re.search(pattern, settlement_content)
            if match:
                groups = match.groups()
                data[f'Settlement_Total{entry_type.capitalize()}_CreditAmount'] = parse_amount(groups[0]) if groups[0] else ''
                data[f'Settlement_Total{entry_type.capitalize()}_DebitAmount'] = parse_amount(groups[1]) if groups[1] else ''
                data[f'Settlement_Total{entry_type.capitalize()}_TotalAmount'] = parse_amount(groups[2]) if groups[2] else ''
        
        # Parse Net Settlement
        net_match = re.search(r'NET SETTLEMENT AMOUNT\s+([\d,]+\.\d{2})?\s*([\d,]+\.\d{2})?\s*([\d,]+\.\d{2}[A-Z]{2}?)?', content)
        if net_match:
            groups = net_match.groups()
            data['Settlement_Net_CreditAmount'] = parse_amount(groups[0]) if groups[0] else ''
            data['Settlement_Net_DebitAmount'] = parse_amount(groups[1]) if groups[1] else ''
            data['Settlement_Net_TotalAmount'] = parse_amount(groups[2]) if groups[2] else ''

    return data



def transform_report_data_to_rows(data: dict) -> pd.DataFrame:
    # Main metadata columns
    metadata_cols = ['ReportID', 'ReportingFor', 'RollupTo', 'FundsXferEntity', 
                    'ProcDate', 'ReportDate', 'SettlementCurrency']
    
    # Define complete structure with all possible MinorTypes
    sections = [
        {
            'MajorType': 'Interchange',
            'MinorTypes': ['TotalAcquirer', 'TotalIssuer', 'TotalOther', 'Total'],
            'Fields': ['Count', 'CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'Reimbursement',
            'MinorTypes': ['TotalAcquirer', 'TotalIssuer', 'TotalOther', 'Total'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'VisaCharges',
            'MinorTypes': ['TotalAcquirer', 'TotalIssuer', 'TotalOther', 'Total'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'Settlement',
            'MinorTypes': ['TotalIssuer', 'Net'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        }
    ]
    
    rows = []
    
    for section in sections:
        for minor_type in section['MinorTypes']:
            row = {col: data.get(col, '') for col in metadata_cols}
            row['MajorType'] = section['MajorType']
            row['MinorType'] = minor_type
            
            # Get all fields for this combination
            for field in section['Fields']:
                key = f"{section['MajorType']}_{minor_type}_{field}"
                value = data.get(key, '')
                
                # Special handling for numeric values
                if isinstance(value, str) and value.replace('.','',1).isdigit():
                    value = float(value)
                row[field] = value
            
            rows.append(row)
    
    # Create DataFrame with consistent column order
    df = pd.DataFrame(rows)
    column_order = metadata_cols + ['MajorType', 'MinorType', 'Count', 
                                  'CreditAmount', 'DebitAmount', 'TotalAmount']
    return df[column_order]

@router.post("/process-visa-report")
async def process_visa_report(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        contents = await file.read()
        parsed_data = parse_visa_report(contents.decode("utf-8"))
        df = transform_report_data_to_rows(parsed_data)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            output_path = tmp.name
            df.to_excel(output_path, index=False)

        background_tasks.add_task(os.unlink, output_path)

        return FileResponse(
            output_path,
            filename="visa_report.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            background=background_tasks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Visa report: {str(e)}")