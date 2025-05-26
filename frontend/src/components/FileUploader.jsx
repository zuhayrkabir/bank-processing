import { useState } from "react";
import axios from "axios";
import {
  Box,
  Button,
  TextField,
  Select,
  MenuItem,
  Typography,
  CircularProgress,
  Paper,
} from "@mui/material";

function FileUploader() {
  const [file, setFile] = useState(null);
  const [filters, setFilters] = useState([{ column: "", operation: "", value: "" }]);
  const [loading, setLoading] = useState(false);

  const operations = [ "=", "!=", ">", "<", ">=", "<=" ];

  const handleFilterChange = (index, field, value) => {
    const updated = [...filters];
    updated[index][field] = value;
    setFilters(updated);
  };

  const addFilter = () => {
    setFilters([...filters, { column: "", operation: "", value: "" }]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return alert("Please upload a file first.");
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);
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
      alert("❌ Failed to upload and process file.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper elevation={3} sx={{ maxWidth: 600, margin: "auto", padding: 4, mt: 5 }}>
      <Typography variant="h5" mb={3} align="center">
        📁 Upload Excel & Apply Filters
      </Typography>
      <form onSubmit={handleSubmit}>
        <Button variant="contained" component="label">
          Choose File
          <input
            type="file"
            hidden
            accept=".xlsx"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </Button>
        {file && (
          <Typography variant="body2" mt={1}>
            Selected file: {file.name}
          </Typography>
        )}

        {filters.map((filter, idx) => (
          <Box key={idx} display="flex" gap={2} mt={2} alignItems="center">
            <TextField
              label="Column"
              value={filter.column}
              onChange={(e) => handleFilterChange(idx, "column", e.target.value)}
              fullWidth
            />
            <Select
              value={filter.operation}
              onChange={(e) => handleFilterChange(idx, "operation", e.target.value)}
              sx={{ width: 80 }}
              displayEmpty
            >
              <MenuItem value="">Op</MenuItem>
              {operations.map((op) => (
                <MenuItem key={op} value={op}>
                  {op}
                </MenuItem>
              ))}
            </Select>
            <TextField
              label="Value"
              value={filter.value}
              onChange={(e) => handleFilterChange(idx, "value", e.target.value)}
              fullWidth
            />
          </Box>
        ))}

        <Button sx={{ mt: 2 }} onClick={addFilter} variant="outlined">
          + Add Filter
        </Button>

        <Box mt={3} textAlign="center">
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={loading}
            startIcon={loading && <CircularProgress size={20} />}
          >
            {loading ? "Processing..." : "🚀 Upload & Filter"}
          </Button>
        </Box>
      </form>
    </Paper>
  );
}

export default FileUploader;
