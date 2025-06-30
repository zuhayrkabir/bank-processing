import { useState } from "react";
import axios from "axios";


function FileUploader() {
  const [activeTab, setActiveTab] = useState("visa"); // Only visa tab now
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState("");

  // Add this state
  const [reportAction, setReportAction] = useState('new'); // 'new' or 'aggregate'
  const [existingReport, setExistingReport] = useState(null);
  const [excelFile, setExcelFile] = useState(null);

  // State for manual entry (simplified version)
  const [manualData, setManualData] = useState({
  ReportID: '',
  ReportingFor: '',
  TransactionType: '',
  RollupTo: '',
  FundsXferEntity: '',
  SettlementCurrency: '',
  MajorType: '',
  MinorType: '',
  ProcessingDate: '',
  ReportingData: '',
  CreditAccount: '',
  DebitAccount: ''
});



  const dropdownOptions = {
  ReportID: ['VSS-110'],
  ReportingFor: ['1000313555 BA INT', '1000313557 BA 463764 INT', '1000313559 BA 463766 INT', '1000313562 BA 463764 DOM', '1000513697 BIN 469343 INTL', '1000513698 BIN 469343 NNSS', '1000670630 BIN 403993 INTL', '1000670631 BIN 403993 NNSS', '1000728502 41993000 INTL', '1000728503 41993000 NNSS', '9000497680 435634 VDIRECT', '9000497681 435634 NW2', '9000497682 435634 SMSVROL', '9000497686 435634 ALL', '9000533759 405736 MVISAORI', '9000533760 405736 ALL', '9000533761 405736 NW2', '9000533762 405736 SMSVROL'],
  TransactionType: ['International Settlement Service', 'Bangladesh National Net Service'],
  RollupTo: ['1000313555 BA INT', '1000313560 BA DOM', '9000497680 435634 VDIRECT', '9000533759 405736 MVISAORI'],
  FundsXferEntity: ['1000313555 BA INT', '1000313560 BA DOM'],
  SettlementCurrency: ['USD', 'BDT'],
  MajorType: ['Interchange', 'Reimbursement', 'Visa Charges', 'Total'],
  MinorType: ['Acquirer', 'Issuer', 'Other', 'Total', 'Net Settlement Amount']
};



  const handleManualSubmit = async (e) => {
    e.preventDefault();
    setIsProcessing(true);
    setError("");

    try {
      console.log("Submitting manual data:", manualData);
      // Here you would send the data to your backend
      // const response = await axios.post("/api/manual-entry", manualData);
      alert("Data submitted successfully!");
    } catch (err) {
      setError("Failed to submit data: " + err.message);
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleManualInputChange = (e) => {
    const { name, value } = e.target;
    setManualData(prev => ({
      ...prev,
      [name]: value
    }));
  };


  const handleVisaSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("⚠️ Please upload a Visa Report TXT file.");
      return;
    }

    setIsProcessing(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await axios.post("http://localhost:8000/process-visa-report", formData, {
        responseType: "blob",
      });

      // Extract filename from headers
      const disposition = res.headers["content-disposition"];
      let filename = "visa_report.xlsx"; // default
      if (disposition && disposition.includes("filename=")) {
        const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (match && match[1]) {
          filename = match[1].replace(/['"]/g, '');
        }
      }

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      alert("✅ Visa report saved and converted to excel file");
    } catch (err) {
      console.error(err);
      setError("❌ Failed to process Visa Report.");
    } finally {
      setIsProcessing(false);
    }
  };


  const handleVisaSaveToDb = async () => {
    const output = "database";

    if (!file) {
      setError("⚠️ Please upload a Visa Report TXT file.");
      return;
    }

    setIsProcessing(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("output", output);

      const res = await axios.post("http://localhost:8000/process-visa-report", formData, {
        responseType: "blob",
      });

      // Extract filename from Content-Disposition header
      const disposition = res.headers["content-disposition"];
      let filename = "visa_report.db"; // Default
      if (disposition && disposition.includes("filename=")) {
        const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (match && match[1]) {
          filename = match[1].replace(/['"]/g, '');
        }
      }

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();

      alert("✅ Visa report saved to database and file downloaded.");
    } catch (err) {
      console.error(err);
      setError("❌ Failed to save Visa Report to database.");
    } finally {
      setIsProcessing(false);
    }
  };



  // Add this debug line right before your return:
console.log("Current tab:", activeTab); 

  return (
    <div style={{
      height: "180vh",
      width: "100vw",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      margin: 0,
      backgroundColor: "#00688b",
    }}>
      {/* Left Image Container */}
      <div style={{
        flex: 1,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
      }}>
        <img 
          src="/bank_asia.jpg" 
          alt="Left Decoration"
          style={{
            maxHeight: "80%",
            maxWidth: "80%",
            objectFit: "contain",
          }}
        />
      </div>

      {/* Main Content */}
      <div style={{
        padding: "40px 20px",
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        width: "600px",
        backgroundColor: "#f5f5f5",
        borderRadius: "10px",
        boxShadow: "0 8px 20px rgba(0,0,0,0.12)",
        margin: "0 20px",
        flexShrink: 0,
      }}>
        {/* Tab Selector */}
        <div style={{ 
          display: "flex", 
          justifyContent: "center", 
          marginBottom: "25px",
          gap: "10px"
        }}>
          <button
            onClick={() => setActiveTab("visa")}
            style={{
              padding: "12px 24px",
              backgroundColor: activeTab === "visa" ? "#4a6bff" : "#ddd",
              color: activeTab === "visa" ? "white" : "#333",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              fontWeight: "600",
              fontSize: "15px",
              transition: "all 0.3s"
            }}
          >
            💳 Visa Report
          </button>
          <button
            onClick={() => setActiveTab("manual")}
            style={{
              padding: "12px 24px",
              backgroundColor: activeTab === "manual" ? "#4a6bff" : "#ddd",
              color: activeTab === "manual" ? "white" : "#333",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              fontWeight: "600",
              fontSize: "15px",
              transition: "all 0.3s"
            }}
          >
            ✏️ Manual Entry
          </button>
        </div>
        <h1 style={{
          textAlign: "center",
          marginBottom: "30px",
          color: "#000000",
          fontWeight: "700",
          fontSize: "2rem",
        }}>
          {activeTab === "visa" ? "💳 Visa Report Processor" : "✏️ Manual Data Entry"}
        </h1>

      


        {activeTab === "visa" ? (
        <form onSubmit={handleVisaSubmit} style={{ textAlign: "center" }}>
          <label
            htmlFor="visa-file-upload"
            style={{
              display: "inline-block",
              padding: "12px 20px",
              backgroundColor: "#555",
              color: "white",
              borderRadius: "8px",
              cursor: "pointer",
              marginBottom: "20px",
              fontWeight: "600",
              fontSize: "15px",
            }}
          >
            💳 Choose Visa Report (TXT)
          </label>
          <input
            id="visa-file-upload"
            type="file"
            accept=".txt"
            onChange={(e) => setFile(e.target.files[0])}
            style={{ display: "none" }}
            required
          />
          {file && (
            <p style={{ marginTop: "1px", color: "#333", fontWeight: "600" }}>
              &#9989; Selected file: {file.name}
            </p>
          )}
          <div style={{
            backgroundColor: "#f8f9fa",
            padding: "15px",
            borderRadius: "8px",
            margin: "20px 0",
            textAlign: "left",
            borderLeft: "4px solid #4a6bff",
          }}>
            <p style={{ margin: "0 0 10px 0", fontWeight: "600", color: "black" }}>
              Will extract:
            </p>
            <ul style={{ paddingLeft: "20px", margin: 0 }}>
              <li style={{ color: "black" }}>Report headers (ID, dates, currency)</li>
              <li style={{ color: "black" }}>Interchange values</li>
              <li style={{ color: "black" }}>Reimbursement fees</li>
              <li style={{ color: "black" }}>Visa charges</li>
              <li style={{ color: "black" }}>Net settlement amounts</li>
            </ul>
          </div>

          <button
            type="button"
            onClick={handleVisaSaveToDb}
            disabled={isProcessing}
            style={{
              padding: "14px 40px",
              backgroundColor: isProcessing ? "#777" : "#2a9d8f",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: isProcessing ? "not-allowed" : "pointer",
              fontWeight: "700",
              fontSize: "18px",
              boxShadow: "0 6px 14px rgba(0,0,0,0.3)",
              transition: "all 0.3s",
              marginBottom: "15px",
              width: "100%",
            }}
          >
            {isProcessing ? "Processing..." : "💾 Save to Database"}
          </button>

          <button
            type="submit"
            disabled={isProcessing}
            style={{
              padding: "14px 40px",
              backgroundColor: isProcessing ? "#777" : "#333",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: isProcessing ? "not-allowed" : "pointer",
              fontWeight: "700",
              fontSize: "18px",
              boxShadow: "0 6px 14px rgba(0,0,0,0.3)",
              transition: "all 0.3s",
            }}
          >
            {isProcessing ? "Processing..." : "🚀 Process Visa Report to Excel File"}
          </button>

          {error && (
            <div style={{
              backgroundColor: "#ffebee",
              color: "#d32f2f",
              padding: "10px",
              borderRadius: "4px",
              marginTop: "20px",
              textAlign: "center",
              fontWeight: "600",
            }}>
              {error}
            </div>
          )}
        </form>


      ) : (
          <form onSubmit={handleManualSubmit} style={{ color: "black" }}>
  <div style={{
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "15px",
    marginBottom: "25px",
  }}>
    {/* Dropdown fields */}
    {Object.entries(dropdownOptions).map(([fieldName, options]) => (
      <div key={fieldName} style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
        <label style={{ 
          fontSize: "14px", 
          color: "black",
          fontWeight: "bold",
          marginBottom: "4px"
        }}>
          {fieldName === 'ReportID' ? 'Report ID' : 
           fieldName.replace(/([A-Z])/g, ' $1').trim()}:
        </label>
        <select
          name={fieldName}
          value={manualData[fieldName]}
          onChange={handleManualInputChange}
          style={{
            padding: "10px",
            fontSize: "14px",
            width: "100%",
            minWidth: "220px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            backgroundColor: "#fff"
          }}
          required
        >
          <option value="">Select {fieldName.replace(/([A-Z])/g, ' $1').trim()}</option>
          {options.map(option => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </div>
    ))}

    {/* New Date Fields */}
    <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
      <label style={{ 
        fontSize: "14px", 
        color: "black",
        fontWeight: "bold",
        marginBottom: "4px"
      }}>
        Processing Date:
      </label>
      <input
        type="date"
        name="processingDate"
        value={manualData.processingDate || ''}
        onChange={handleManualInputChange}
        style={{
          padding: "10px",
          fontSize: "14px",
          width: "100%",
          minWidth: "220px",
          borderRadius: "6px",
          border: "1px solid #ccc",
          backgroundColor: "#fff"
        }}
        required
      />
    </div>

    <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
      <label style={{ 
        fontSize: "14px", 
        color: "black",
        fontWeight: "bold",
        marginBottom: "4px"
      }}>
        Report Date:
      </label>
      <input
        type="date"
        name="reportDate"
        value={manualData.reportDate || ''}
        onChange={handleManualInputChange}
        style={{
          padding: "10px",
          fontSize: "14px",
          width: "100%",
          minWidth: "220px",
          borderRadius: "6px",
          border: "1px solid #ccc",
          backgroundColor: "#fff"
        }}
        required
      />
    </div>

    {/* Text input fields for accounts */}
    {['CreditAccount', 'DebitAccount'].map(fieldName => (
      <div key={fieldName} style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
        <label style={{ 
          fontSize: "14px", 
          color: "black",
          fontWeight: "bold",
          marginBottom: "4px"
        }}>
          {fieldName.replace(/([A-Z])/g, ' $1').trim()}:
        </label>
        <input
          type="text"
          name={fieldName}
          value={manualData[fieldName]}
          onChange={handleManualInputChange}
          style={{
            padding: "10px",
            fontSize: "14px",
            width: "100%",
            minWidth: "220px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            backgroundColor: "#fff"
          }}
          required
        />
      </div>
    ))}
  </div>

    {/* Excel File Upload Section */}
  <div style={{ marginBottom: "20px", marginTop: "20px" }}>
    <label
      htmlFor="excel-file-upload"
      style={{
        display: "inline-block",
        padding: "12px 20px",
        backgroundColor: "#2a9d8f",
        color: "white",
        borderRadius: "8px",
        cursor: "pointer",
        fontWeight: "600",
        fontSize: "15px",
        width: "93%",
        textAlign: "center",
        boxShadow: "0 4px 8px rgba(0,0,0,0.1)"
      }}
    >
      📤 Upload Processed txt to Excel File (.xlsx)
    </label>
    <input
      id="excel-file-upload"
      type="file"
      accept=".xlsx"
      onChange={(e) => {
        if (e.target.files && e.target.files[0]) {
          const file = e.target.files[0];
          if (file.name.endsWith('.xlsx')) {
            // Handle the Excel file upload here
            console.log("Excel file selected:", file.name);
            // You can add your file processing logic here
          } else {
            alert("Please upload only .xlsx files");
            e.target.value = ""; // Reset the file input
          }
        }
      }}
      style={{ display: "none" }}
    />
  </div>

  {/* Excel File Upload Button */}
<div style={{ marginBottom: "15px" }}>
  <label
    htmlFor="excel-file-upload"
    style={{
      display: "inline-block",
      padding: "10px 20px",
      backgroundColor: excelFile ? "#ff7f50" : "#6c757d",
      color: "white",
      borderRadius: "8px",
      cursor: "pointer",
      fontWeight: "700",
      fontSize: "15px",
      width: "93%",
      textAlign: "center",
      boxShadow: "0 6px 14px rgba(0,0,0,0.3)",
      transition: "all 0.3s",
    }}
  >
    {excelFile ? `📊 ${excelFile.name}` : "📤 Upload Existing Report (if aggregating) (.xlsx)"}
  </label>
  <input
    id="excel-file-upload"
    type="file"
    accept=".xlsx"
    onChange={(e) => {
      if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        if (file.name.endsWith('.xlsx')) {
          setExcelFile(file);
          console.log("Excel file selected:", file.name);
        } else {
          setError("Please upload only .xlsx files");
          e.target.value = "";
        }
      }
    }}
    style={{ display: "none" }}
  />
</div>


  {/* Submit button */}
  <button
    type="submit"
    disabled={isProcessing}
    style={{
      padding: "14px 40px",
      backgroundColor: isProcessing ? "#777" : "#4a6bff",
      color: "white",
      border: "none",
      borderRadius: "8px",
      cursor: isProcessing ? "not-allowed" : "pointer",
      fontWeight: "700",
      fontSize: "18px",
      boxShadow: "0 6px 14px rgba(0,0,0,0.3)",
      transition: "all 0.3s",
      width: "100%",
      marginTop: "20px"
    }}
  >
    {isProcessing ? "Processing..." : "Submit Manual Entry"}
  </button>
</form>
        )}

                  {/* Error message (works for both tabs) */}
                  {error && (
                    <div style={{
                      backgroundColor: "#ffebee",
                      color: "#d32f2f",
                      padding: "10px",
                      borderRadius: "4px",
                      marginTop: "20px",
                      textAlign: "center",
                      fontWeight: "600",
                    }}>
                      {error}
                    </div>
                  )}
                </div>
        

      {/* Right Image Container */}
      <div style={{
        flex: 1,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
      }}>
        <img 
          src="/bankasia-building.jpg" 
          alt="Right Decoration"
          style={{
            maxHeight: "80%",
            maxWidth: "80%",
            objectFit: "contain",
          }}
        />
      </div>
    </div>
  );
};

export default FileUploader;