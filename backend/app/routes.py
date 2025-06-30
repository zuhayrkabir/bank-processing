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
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import VisaReportLine
import sqlite3
from fastapi.responses import StreamingResponse
import mimetypes
from fastapi import Depends
from fastapi import Query
from fastapi import Form
from fastapi import Request
from fastapi import Response
from fastapi.exceptions import HTTPException
import traceback
from fastapi import Body
from pydantic import BaseModel
from pydantic import validator
import re

router = APIRouter()


# ========= VISA REPORT PARSING ROUTE =========
def parse_visa_report(content: str) -> Dict:
    """Parses Visa report and prints all values for verification"""
    
    def parse_amount(amount_str):
        """Helper to parse amounts with commas and CR/DB flags"""
        original = amount_str
        if not amount_str or str(amount_str).strip() in ('', '0.00'):
            return 0.0
        amount_str = str(amount_str).replace(',', '').strip()
        if 'CR' in amount_str:
            result = float(amount_str.replace('CR', ''))
        elif 'DB' in amount_str:
            result = -float(amount_str.replace('DB', ''))
        else:
            try:
                result = float(amount_str)
            except ValueError:
                result = 0.0
        print(f"    🪙 Parsing amount: '{original}' → {result}")
        return result

    def parse_count(count_str):
        """Helper to parse counts with commas"""
        original = count_str
        if not count_str or str(count_str).strip() in ('', '0'):
            return 0
        try:
            result = int(str(count_str).replace(',', ''))
        except ValueError:
            result = 0
        print(f"    🔢 Parsing count: '{original}' → {result}")
        return result

    # Initialize data dictionary
    data = {}

    print("\n" + "="*40)
    print("📋 STARTING REPORT PARSING 📋")
    print("="*40 + "\n")

    # Header patterns
    headers = {
        'ReportID': r'REPORT ID:\s+(VSS-\d+)',
        'ReportingFor': r'REPORTING FOR:\s+(.+?)\s+PROC',
        'RollupTo': r'ROLLUP TO:\s+(.+?)\s+SETTLEMENT',
        'FundsXferEntity': r'FUNDS XFER ENTITY:\s+(.+?)\n',
        'ProcDate': r'PROC DATE:\s+(\d{2}[A-Za-z]{3}\d{2})',
        'ReportDate': r'REPORT DATE:\s+(\d{2}[A-Za-z]{3}\d{2})',
        'SettlementCurrency': r'SETTLEMENT CURRENCY:\s+([A-Z]{3})'
    }

    print("\n📌 PARSING HEADERS 📌")
    for field, pattern in headers.items():
        if match := re.search(pattern, content):
            data[field] = match.group(1).strip()
            print(f"  ✅ {field}: {data[field]}")
        else:
            print(f"  ❌ {field}: NOT FOUND")

    # Define section patterns with explicit total patterns
    sections = [
        {
            'name': 'Interchange',
            'pattern': r'INTERCHANGE VALUE(.*?)REIMBURSEMENT FEES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'has_count': True,
            'total_pattern': r'TOTAL INTERCHANGE VALUE\s+([\d,]+)\s+([\d,]+\.\d{2}(?:CR|DB)?)\s+([\d,]+\.\d{2}(?:CR|DB)?)\s+([\d,]+\.\d{2}(?:CR|DB)?)',
            'total_label': 'INTERCHANGE VALUE'
        },
        {
            'name': 'Reimbursement',
            'pattern': r'REIMBURSEMENT FEES(.*?)VISA CHARGES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'has_count': False,
            'total_pattern': r'TOTAL REIMBURSEMENT FEES\s+([\d,]+\.\d{2}(?:CR|DB)?)\s+([\d,]+\.\d{2}(?:CR|DB)?)\s+([\d,]+\.\d{2}(?:CR|DB)?)',
            'total_label': 'REIMBURSEMENT FEES'
        },
        {
            'name': 'VisaCharges',
            'pattern': r'VISA CHARGES(.*?)TOTAL VISA CHARGES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'has_count': False,
            'total_pattern': r'TOTAL VISA CHARGES\s+([\d,]+\.\d{2}(?:CR|DB)?)\s+([\d,]+\.\d{2}(?:CR|DB)?)\s+([\d,]+\.\d{2}(?:CR|DB)?)',
            'total_label': 'VISA CHARGES'
        }
    ]

    # Dictionary to store the key totals we want to highlight
    key_totals = {}

    # Process each section
    for section in sections:
        print(f"\n🔍 PARSING {section['name'].upper()} SECTION 🔍")
        if section_match := re.search(section['pattern'], content, re.DOTALL):
            section_content = section_match.group(1)

            for line_type in section['line_types']:
                print(f"\n  📝 Processing {line_type} line:")
                
                # More flexible line pattern that handles variable whitespace
                if section['has_count']:
                    pattern = rf'TOTAL {line_type}\s+([\d,]+)\s+([\d,]+\.\d{{2}}(?:CR|DB)?)\s+([\d,]+\.\d{{2}}(?:CR|DB)?)\s+([\d,]+\.\d{{2}}(?:CR|DB)?)'
                else:
                    pattern = rf'TOTAL {line_type}\s+([\d,]+\.\d{{2}}(?:CR|DB)?)\s+([\d,]+\.\d{{2}}(?:CR|DB)?)\s+([\d,]+\.\d{{2}}(?:CR|DB)?)'

                if match := re.search(pattern, section_content):
                    groups = match.groups()
                    print(f"    📊 Raw match groups: {groups}")

                    if section['has_count']:
                        count = parse_count(match.group(1))
                        data[f"{section['name']}_{line_type}_Count"] = count
                        credit = parse_amount(match.group(2))
                        debit = parse_amount(match.group(3))
                        total = parse_amount(match.group(4))
                    else:
                        credit = parse_amount(match.group(1))
                        debit = parse_amount(match.group(2))
                        total = parse_amount(match.group(3))

                    data[f"{section['name']}_{line_type}_CreditAmount"] = credit
                    data[f"{section['name']}_{line_type}_DebitAmount"] = debit
                    data[f"{section['name']}_{line_type}_TotalAmount"] = total

                    print(f"    💾 Stored values:")
                    if section['has_count']:
                        print(f"      🔢 Count: {count}")
                    print(f"      💰 Credit: {credit}")
                    print(f"      💸 Debit: {debit}")
                    print(f"      🏦 Total: {total}")
                else:
                    print(f"    ⚠️ No match found for {line_type}")

            # Parse section total using the specific pattern
            print(f"\n  🏷️ Processing {section['name']} TOTAL:")
            if 'total_pattern' in section:
                total_pattern = section['total_pattern']
                print(f"    Using specific pattern: {total_pattern}")
                
                if total_match := re.search(total_pattern, content):
                    groups = total_match.groups()
                    print(f"    📊 Raw total match groups: {groups}")

                    if section['has_count']:
                        total_count = parse_count(total_match.group(1))
                        data[f"{section['name']}_Total_Count"] = total_count
                        total_credit = parse_amount(total_match.group(2))
                        total_debit = parse_amount(total_match.group(3))
                        total_total = parse_amount(total_match.group(4))
                    else:
                        total_credit = parse_amount(total_match.group(1))
                        total_debit = parse_amount(total_match.group(2))
                        total_total = parse_amount(total_match.group(3))

                    data[f"{section['name']}_Total_CreditAmount"] = total_credit
                    data[f"{section['name']}_Total_DebitAmount"] = total_debit
                    data[f"{section['name']}_Total_TotalAmount"] = total_total

                    # Store the total for this section in our key_totals dictionary
                    key_totals[section['name']] = total_total

                    print(f"    💾 Stored total values:")
                    if section['has_count']:
                        print(f"      🔢 Total Count: {total_count}")
                    print(f"      💰 Total Credit: {total_credit}")
                    print(f"      💸 Total Debit: {total_debit}")
                    print(f"      🏦 Total Total: {total_total}")
                else:
                    print(f"    ⚠️ No total match found using specific pattern for {section['name']}")
            else:
                print(f"    ⚠️ No total pattern defined for {section['name']}")

        # Parse the "TOTAL" section that appears right before NET SETTLEMENT
        # Parse the "TOTAL" section that appears right before NET SETTLEMENT
        # In the FinalTotals parsing section, replace with this:

        print("\n" + "="*40)
        print("💳 PARSING FINAL TOTALS SECTION 💳")
        print("="*40 + "\n")

            # Replace the totals_pattern with this more precise version:
    totals_pattern = (
        r'^\s*TOTAL\s+ACQUIRER\s+([\d,]+\.\d{2}[A-Z]*)\s+([\d,]+\.\d{2}[A-Z]*)\s+([\d,]+\.\d{2}[A-Z]*)\s*$\n'
        r'^\s*TOTAL\s+ISSUER\s+([\d,]+\.\d{2}[A-Z]*)\s+([\d,]+\.\d{2}[A-Z]*)\s+([\d,]+\.\d{2}[A-Z]*)\s*$\n'
        r'^\s*TOTAL\s+OTHER\s+([\d,]+\.\d{2}[A-Z]*)\s+([\d,]+\.\d{2}[A-Z]*)\s+([\d,]+\.\d{2}[A-Z]*)\s*$\n'
        r'(?=\s*NET SETTLEMENT AMOUNT)'
    )

    # And modify the search to work line-by-line
    if totals_match := re.search(totals_pattern, content, re.DOTALL | re.MULTILINE):
        print("Found FINAL TOTALS section")
        
        # Parse all values immediately (no delayed parsing)
        for line_type, groups in [('ACQUIRER', (1, 2, 3)), 
                                ('ISSUER', (4, 5, 6)),
                                ('OTHER', (7, 8, 9))]:
            print(f"\n  📝 Processing {line_type} line:")
            
            credit = parse_amount(totals_match.group(groups[0]))
            debit = parse_amount(totals_match.group(groups[1]))
            total = parse_amount(totals_match.group(groups[2]))
            
            data[f"FinalTotal_{line_type}_CreditAmount"] = credit
            data[f"FinalTotal_{line_type}_DebitAmount"] = debit
            data[f"FinalTotal_{line_type}_TotalAmount"] = total
            
            print(f"    📊 Raw values: {totals_match.group(groups[0])}, {totals_match.group(groups[1])}, {totals_match.group(groups[2])}")
            print(f"    💾 Stored values: {credit}, {debit}, {total}")


    # Parse net settlement with more flexible pattern
    print("\n" + "="*40)
    print("💵 PARSING NET SETTLEMENT 💵")
    print("="*40 + "\n")
    net_pattern = r'NET SETTLEMENT AMOUNT\s+([\d,]+\.\d{2}(?:CR|DB)?)\s+([\d,]+\.\d{2}(?:CR|DB)?)\s+([\d,]+\.\d{2}(?:CR|DB)?)'
    if net_match := re.search(net_pattern, content):
        groups = net_match.groups()
        print(f"  📊 Raw match groups: {groups}")
        
        credit = parse_amount(net_match.group(1))
        debit = parse_amount(net_match.group(2))
        total = parse_amount(net_match.group(3))

        data['Settlement_Net_CreditAmount'] = credit
        data['Settlement_Net_DebitAmount'] = debit
        data['Settlement_Net_TotalAmount'] = total

        # Store the net settlement amount in our key_totals dictionary
        key_totals['NetSettlement'] = total

        print(f"  💾 Stored values:")
        print(f"    💰 Credit: {credit}")
        print(f"    💸 Debit: {debit}")
        print(f"    🏦 Total: {total}")
    else:
        print("  ⚠️ No match found for NET SETTLEMENT AMOUNT")

    # Print the key totals in a prominent way
    print("\n" + "="*40)
    print("💰 KEY TOTALS 💰")
    print("="*40)
    print(f"🔄 Interchange Total: {key_totals.get('Interchange', 'N/A')}")
    print(f"💳 Reimbursement Total: {key_totals.get('Reimbursement', 'N/A')}")
    print(f"💲 Visa Charges Total: {key_totals.get('VisaCharges', 'N/A')}")
    print(f"🏦 Net Settlement Amount: {key_totals.get('NetSettlement', 'N/A')}")
    print("="*40 + "\n")

    print("\n" + "="*40)
    print("🎉 FINAL PARSED DATA 🎉")
    print("="*40 + "\n")
    for key, value in data.items():
        print(f"🔑 {key}: {value}")

    return data




def transform_report_data_to_rows(data: dict) -> pd.DataFrame:
    # First split ReportingFor into ReportingFor and TransactionType
    reporting_for_full = data.get("ReportingFor", "")
    split_parts = re.split(r'\s{2,}', reporting_for_full.strip())  # split on 2+ spaces

    if len(split_parts) == 2:
        data["ReportingFor"] = split_parts[0]
        data["TransactionType"] = split_parts[1]
    else:
        data["ReportingFor"] = reporting_for_full
        data["TransactionType"] = ""

    metadata_cols = ['ReportID', 'ReportingFor', 'TransactionType', 'RollupTo', 'FundsXferEntity', 
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
            'MajorType': 'FinalTotal',
            'MinorTypes': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount'],
            'HasCount': False  # Add this flag
        },
        {
            'MajorType': 'Settlement',
            'MinorTypes': ['Net'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        }
    ]

    rows = []

    for section in sections:
        for minor_type in section['MinorTypes']:
            row = {col: data.get(col, '') for col in metadata_cols}
            row['MajorType'] = section['MajorType']
            row['MinorType'] = "Net Settlement Amount" if minor_type == 'Net' else minor_type

            for field in section['Fields']:
                if minor_type == 'Net':
                    key = f"Settlement_Net_{field}"
                elif section['MajorType'] == 'FinalTotal':
                    for field in section['Fields']:
                        key = f"FinalTotal_{minor_type}_{field}"
                        # Use direct value if exists, otherwise 0
                        row[field] = data.get(key, 0.0 if 'Amount' in field else 0)
                    
                    # Special case: Ensure ISSUER shows the correct values
                    if minor_type == 'ISSUER':
                        row['CreditAmount'] = data.get('FinalTotal_ISSUER_CreditAmount', 0)
                        row['DebitAmount'] = data.get('FinalTotal_ISSUER_DebitAmount', 0)
                        row['TotalAmount'] = data.get('FinalTotal_ISSUER_TotalAmount', 0)
                elif minor_type == 'Total':
                    key = f"{section['MajorType']}_Total_{field}"
                else:
                    key = f"{section['MajorType']}_{minor_type}_{field}"

                value = data.get(key)
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





def save_df_to_sqlite(df, db_path="parsed_report.db", table_name="visa_report"):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    return db_path




@router.post("/process-visa-report")
async def process_visa_report(
    file: UploadFile = File(...),
    output: str = Form("excel")
):
    contents = await file.read()
    content_str = contents.decode("utf-8")
    df = process_multiple_visa_reports(content_str)

    # Extract report_id for use in filenames
    if len(df) > 1:
        second_row = df.iloc[1]
        report_id = str(second_row.get('ReportID', 'VSS-000')).replace("/", "-")
        proc_date = str(second_row.get('ProcDate', 'nodate')).replace("/", "-")
        report_date = str(second_row.get('ReportDate', 'nodate')).replace("/", "-")
    else:
        report_id = "VSS-000"
        proc_date = "nodate"
        report_date = "nodate"

    # Database mode
    if output == "database":
        db_path = save_df_to_sqlite(df)
        db_filename = f"{report_id}.db"
        return FileResponse(
            db_path,
            media_type="application/octet-stream",
            filename=db_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{db_filename}"'
            }
        )

    # Excel mode
    excel_filename = f"{report_id}.{proc_date}.{report_date}.xlsx"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        output_path = tmp.name
        df.to_excel(output_path, index=False)
        autosize_excel_columns(output_path)

    file_stream = open(output_path, "rb")
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{excel_filename}"'
        }
    )


