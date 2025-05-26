import { useState } from "react";
import axios from "axios";

function FileUploader() {
  const [activeTab, setActiveTab] = useState("txt"); // 'txt' or 'excel'
  const [file, setFile] = useState(null);
  const [filters, setFilters] = useState([{ column: "", operation: "", value: "" }]);

  const handleFilterChange = (index, field, value) => {
    const updated = [...filters];
    updated[index][field] = value;
    setFilters(updated);
  };

  const addFilter = () => {
    setFilters([...filters, { column: "", operation: "", value: "" }]);
  };

  const handleExcelSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("⚠️ Please upload a file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("filters", JSON.stringify(filters));
    formData.append("filetype", "xlsx");

    try {
      const res = await axios.post("http://localhost:8000/process", formData, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "filtered_file.xlsx");
      document.body.appendChild(link);
      link.click();
    } catch (err) {
      console.error(err);
      alert("❌ Failed to upload and process Excel file.");
    }
  };

  const handleTxtSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("⚠️ Please upload a file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("filetype", "txt");

    try {
      const res = await axios.post("http://localhost:8000/process", formData, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "converted_file.xlsx");
      document.body.appendChild(link);
      link.click();
    } catch (err) {
      console.error(err);
      alert("❌ Failed to upload and convert TXT file.");
    }
  };

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#eaeaea",
        margin: 0,
      }}
    >
      <div
        style={{
          padding: "40px 20px",
          fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
          maxWidth: "600px",
          width: "100%",
          backgroundColor: "#f5f5f5",
          borderRadius: "10px",
          boxShadow: "0 8px 20px rgba(0,0,0,0.12)",
        }}
      >
        <h1
          style={{
            textAlign: "center",
            marginBottom: "30px",
            color: "#000000", // Black text
            fontWeight: "700",
            fontSize: "2rem",
          }}
        >
          📂 File Processor
        </h1>

        {/* Tabs */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "25px" }}>
          <button
            onClick={() => {
              setActiveTab("txt");
              setFile(null);
            }}
            style={{
              backgroundColor: activeTab === "txt" ? "#333" : "#666",
              border: "none",
              borderRadius: "8px 0 0 8px",
              padding: "12px 30px",
              cursor: "pointer",
              color: "white",
              fontWeight: "600",
              fontSize: "16px",
              boxShadow: activeTab === "txt" ? "0 4px 8px rgba(0,0,0,0.3)" : "none",
              transition: "background-color 0.3s",
            }}
          >
            📄 TXT to Excel
          </button>
          <button
            onClick={() => {
              setActiveTab("excel");
              setFile(null);
            }}
            style={{
              backgroundColor: activeTab === "excel" ? "#333" : "#666",
              border: "none",
              borderRadius: "0 8px 8px 0",
              padding: "12px 30px",
              cursor: "pointer",
              color: "white",
              fontWeight: "600",
              fontSize: "16px",
              boxShadow: activeTab === "excel" ? "0 4px 8px rgba(0,0,0,0.3)" : "none",
              transition: "background-color 0.3s",
            }}
          >
            📊 Excel Filters
          </button>
        </div>

        {/* TXT tab */}
        {activeTab === "txt" && (
          <form onSubmit={handleTxtSubmit} style={{ textAlign: "center" }}>
            <label
              htmlFor="txt-file-upload"
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
              📁 Choose TXT File
            </label>
            <input
              id="txt-file-upload"
              type="file"
              accept=".txt"
              onChange={(e) => setFile(e.target.files[0])}
              style={{ display: "none" }}
              required
            />
            <br />
            <button
              type="submit"
              style={{
                padding: "12px 30px",
                backgroundColor: "#333",
                color: "white",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "16px",
                boxShadow: "0 4px 8px rgba(0,0,0,0.2)",
                transition: "background-color 0.3s",
              }}
            >
              🔄 Convert to Excel
            </button>
          </form>
        )}

        {/* Excel tab */}
        {activeTab === "excel" && (
          <form onSubmit={handleExcelSubmit} style={{ textAlign: "center" }}>
            <label
              htmlFor="excel-file-upload"
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
              📁 Choose Excel File
            </label>
            <input
              id="excel-file-upload"
              type="file"
              accept=".xlsx"
              onChange={(e) => setFile(e.target.files[0])}
              style={{ display: "none" }}
              required
            />
            <br />
            <div style={{ marginBottom: "15px" }}>
              {filters.map((filter, idx) => (
                <div
                  key={idx}
                  style={{
                    marginBottom: "10px",
                    display: "flex",
                    justifyContent: "center",
                    gap: "10px",
                  }}
                >
                  <input
                    placeholder="Column"
                    value={filter.column}
                    onChange={(e) => handleFilterChange(idx, "column", e.target.value)}
                    required
                    style={{
                      padding: "8px",
                      width: "25%",
                      borderRadius: "5px",
                      border: "1px solid #ccc",
                      fontSize: "14px",
                    }}
                  />
                  <select
                    value={filter.operation}
                    onChange={(e) => handleFilterChange(idx, "operation", e.target.value)}
                    required
                    style={{
                      padding: "8px",
                      width: "25%",
                      borderRadius: "5px",
                      border: "1px solid #ccc",
                      backgroundColor: "#333",
                      color: "white",
                      fontWeight: "600",
                      fontSize: "14px",
                    }}
                  >
                    <option value="" disabled>
                      Op
                    </option>
                    <option value="=">=</option>
                    <option value="!=">!=</option>
                    <option value=">">&gt;</option>
                    <option value="<">&lt;</option>
                    <option value=">=">&gt;=</option>
                    <option value="<=">&lt;=</option>
                    <option value="contains">contains</option>
                    <option value="not_contains">does not contain</option>
                  </select>
                  <input
                    placeholder="Value"
                    value={filter.value}
                    onChange={(e) => handleFilterChange(idx, "value", e.target.value)}
                    required
                    style={{
                      padding: "8px",
                      width: "25%",
                      borderRadius: "5px",
                      border: "1px solid #ccc",
                      fontSize: "14px",
                    }}
                  />
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addFilter}
              style={{
                padding: "10px 25px",
                backgroundColor: "#222",
                color: "white",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: "700",
                fontSize: "16px",
                boxShadow: "0 4px 10px rgba(0,0,0,0.25)",
                transition: "background-color 0.3s",
                marginBottom: "20px",
              }}
            >
              ➕ Add Filter
            </button>
            <br />
            <button
              type="submit"
              style={{
                padding: "14px 40px",
                backgroundColor: "#333",
                color: "white",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: "700",
                fontSize: "18px",
                boxShadow: "0 6px 14px rgba(0,0,0,0.3)",
                transition: "background-color 0.3s",
              }}
            >
              🚀 Upload & Filter
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default FileUploader;
