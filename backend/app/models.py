from sqlalchemy import Column, Integer, Float, String
from .database import Base

class VisaReportLine(Base):
    __tablename__ = "visa_report_lines"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String)
    proc_date = Column(String)
    report_date = Column(String)
    major_type = Column(String)
    minor_type = Column(String)
    count = Column(Integer)
    credit_amount = Column(Float)
    debit_amount = Column(Float)
    total_amount = Column(Float)
    crdb_label = Column(String)