import { useState } from "react";
import axios from "axios";

function FileUploader() {
  const [activeTab, setActiveTab] = useState("txt");
  const [txtFile, setTxtFile] = useState(null);
  const [excelFile, setExcelFile] = useState(null);
  const [filters, setFilters] = useState([{ column: "", operation: "", value: "" }]);

  const handleFilterChange = (index, field, value) => {
    const updated = [...filters];
    updated[index][field] = value;
    setFilters(updated);
  };

  const addFilter = () => {
    setFilters([...filters, { column: "", operation: "", value: "" }]);
  };

  const handleTxtSubmit = async (e) => {
    e.preventDefault();
    if (!txtFile) {
      alert("Please upload a TXT file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", txtFile);

    try {
      const res = await axios.post("http://localhost:8000/convert-txt", formData, {
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
      alert("❌ Failed to convert TXT file.");
    }
  };

  const handleExcelSubmit = async (e) => {
    e.preventDefault();
    if (!excelFile) {
      alert("Please upload an Excel file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", excelFile);
    formData.append("filters", JSON.stringify(filters));

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

  return (
    <div style={{ fontFamily: "Arial", padding: "20px" }}>
      <h2>📁 Upload & Process Files</h2>
      <div style={{ marginBottom: "20px" }}>
        <button onClick={() => setActiveTab("txt")} style={{ marginRight: "10px" }}>
          TXT Upload & Convert
        </button>
        <button onClick={() => setActiveTab("excel")}>Excel Upload & Filter</button>
      </div>

      {activeTab === "txt" && (
        <form onSubmit={handleTxtSubmit}>
          <h3>TXT File ➡️ Excel</h3>
          <input type="file" accept=".txt" onChange={e => setTxtFile(e.target.files[0])} required />
          <br /><br />
          <button type="submit">Convert to Excel</button>
        </form>
      )}

      {activeTab === "excel" && (
        <form onSubmit={handleExcelSubmit}>
          <h3>Excel File ➕ Filters</h3>
          <input type="file" accept=".xlsx" onChange={e => setExcelFile(e.target.files[0])} required />
          <br /><br />
          {filters.map((filter, idx) => (
            <div key={idx}>
              <input
                placeholder="Column"
                value={filter.column}
                onChange={e => handleFilterChange(idx, "column", e.target.value)}
                required
              />
              <select
                value={filter.operation}
                onChange={e => handleFilterChange(idx, "operation", e.target.value)}
                required
              >
                <option value="">Op</option>
                <option value="=">=</option>
                <option value="!=">!=</option>
                <option value=">">&gt;</option>
                <option value="<">&lt;</option>
                <option value=">=">&gt;=</option>
                <option value="<=">&lt;=</option>
              </select>
              <input
                placeholder="Value"
                value={filter.value}
                onChange={e => handleFilterChange(idx, "value", e.target.value)}
                required
              />
              <br />
            </div>
          ))}
          <button type="button" onClick={addFilter}>+ Add Filter</button>
          <br /><br />
          <button type="submit">Upload & Filter Excel</button>
        </form>
      )}
    </div>
  );
}

export default FileUploader;
