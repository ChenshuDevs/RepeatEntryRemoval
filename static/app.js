const fileInput = document.getElementById("dataFile");
const processButton = document.getElementById("processButton");
const downloadButton = document.getElementById("downloadButton");
const resultsSection = document.getElementById("resultsSection");
const messageArea = document.getElementById("messageArea");

let currentResult = null;
let comparisonChart = null;
let distributionChart = null;

function showMessage(type, text) {
  const message = document.createElement("div");
  message.className = `message ${type}`;
  message.textContent = text;
  messageArea.appendChild(message);
}

function resetMessages() {
  messageArea.innerHTML = "";
}

function normalizeCell(value) {
  if (value === null || value === undefined) {
    return "";
  }

  if (typeof value === "number" && Number.isInteger(value)) {
    return String(value);
  }

  return String(value).trim();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function parseCsv(file) {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        if (results.errors.length > 0) {
          reject(new Error(results.errors[0].message));
          return;
        }

        resolve({
          headers: results.meta.fields || [],
          rows: results.data,
        });
      },
      error: (error) => reject(error),
    });
  });
}

function parseWorkbook(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const workbook = XLSX.read(event.target.result, { type: "array" });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const rows = XLSX.utils.sheet_to_json(worksheet, { defval: "" });
        const headers = rows.length > 0 ? Object.keys(rows[0]) : [];
        resolve({ headers, rows });
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = () => reject(new Error("Could not read the Excel file."));
    reader.readAsArrayBuffer(file);
  });
}

async function parseFile(file) {
  const extension = file.name.split(".").pop().toLowerCase();
  if (extension === "csv") {
    return parseCsv(file);
  }
  if (extension === "xlsx" || extension === "xls") {
    return parseWorkbook(file);
  }
  throw new Error("Unsupported file type. Use CSV, XLSX, or XLS.");
}

function buildDuplicateGroups(headers, originalRows, normalizedRows, limit = 5) {
  const counts = new Map();
  const firstIndexBySignature = new Map();

  normalizedRows.forEach((normalizedRow, index) => {
    const signature = headers.map((header) => normalizeCell(normalizedRow[header])).join("||");
    counts.set(signature, (counts.get(signature) || 0) + 1);
    if (!firstIndexBySignature.has(signature)) {
      firstIndexBySignature.set(signature, index);
    }
  });

  return [...counts.entries()]
    .filter(([, count]) => count > 1)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([signature, count]) => {
      const rowIndex = firstIndexBySignature.get(signature);
      const sampleRow = originalRows[rowIndex];
      return {
        count,
        values: headers.map((header) => sampleRow[header] ?? ""),
      };
    });
}

function processRows(headers, rows) {
  const normalizedRows = rows.map((row) => {
    const normalizedRow = {};
    headers.forEach((header) => {
      normalizedRow[header] = normalizeCell(row[header]);
    });
    return normalizedRow;
  });

  const seen = new Set();
  const cleanedRows = [];

  normalizedRows.forEach((normalizedRow, index) => {
    const signature = headers.map((header) => normalizedRow[header]).join("||");
    if (!seen.has(signature)) {
      seen.add(signature);
      cleanedRows.push(rows[index]);
    }
  });

  const removedRows = rows.length - cleanedRows.length;
  const duplicateRate = rows.length === 0 ? 0 : ((removedRows / rows.length) * 100).toFixed(2);

  return {
    headers,
    originalRows: rows,
    cleanedRows,
    removedRows,
    duplicateRate,
    duplicateGroups: buildDuplicateGroups(headers, rows, normalizedRows),
  };
}

function renderTable(containerId, headers, rows) {
  const container = document.getElementById(containerId);
  if (headers.length === 0) {
    container.innerHTML = '<p class="empty-state">No tabular preview is available for this file.</p>';
    return;
  }

  const previewRows = rows.slice(0, 10);
  const headerHtml = headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("");
  const bodyHtml = previewRows
    .map((row) => {
      const cells = headers.map((header) => `<td>${escapeHtml(row[header] ?? "")}</td>`).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  container.innerHTML = `
    <table>
      <thead>
        <tr>${headerHtml}</tr>
      </thead>
      <tbody>${bodyHtml}</tbody>
    </table>
  `;
}

function renderDuplicateGroups(groups) {
  const container = document.getElementById("duplicateGroups");
  if (groups.length === 0) {
    container.innerHTML = '<p class="empty-state">No duplicate row groups were found in this file.</p>';
    return;
  }

  container.innerHTML = groups
    .map((group) => {
      const values = group.values
        .map((value) => `<span>${escapeHtml(value || "(blank)")}</span>`)
        .join("");
      return `
        <article class="duplicate-item">
          <div class="duplicate-count">${group.count} matches</div>
          <div class="duplicate-values">${values}</div>
        </article>
      `;
    })
    .join("");
}

function destroyCharts() {
  if (comparisonChart) {
    comparisonChart.destroy();
    comparisonChart = null;
  }
  if (distributionChart) {
    distributionChart.destroy();
    distributionChart = null;
  }
}

function renderCharts(summary) {
  destroyCharts();

  comparisonChart = new Chart(document.getElementById("comparisonChart"), {
    type: "bar",
    data: {
      labels: ["Before cleanup", "After cleanup"],
      datasets: [
        {
          label: "Rows",
          data: [summary.originalRows.length, summary.cleanedRows.length],
          backgroundColor: ["#146356", "#f08a24"],
          borderRadius: 14,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, grid: { color: "rgba(39, 45, 39, 0.08)" } },
      },
    },
  });

  distributionChart = new Chart(document.getElementById("distributionChart"), {
    type: "doughnut",
    data: {
      labels: ["Rows kept", "Rows removed"],
      datasets: [
        {
          data: [summary.cleanedRows.length, summary.removedRows],
          backgroundColor: ["#146356", "#f08a24"],
          borderColor: ["#fffaf2", "#fffaf2"],
          borderWidth: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
        },
      },
    },
  });
}

function updateSummary(summary, fileName) {
  document.getElementById("resultFilename").textContent = fileName;
  document.getElementById("rowsBefore").textContent = summary.originalRows.length;
  document.getElementById("rowsAfter").textContent = summary.cleanedRows.length;
  document.getElementById("rowsRemoved").textContent = summary.removedRows;
  document.getElementById("duplicateRate").textContent = `${summary.duplicateRate}%`;

  renderTable("beforeTable", summary.headers, summary.originalRows);
  renderTable("afterTable", summary.headers, summary.cleanedRows);
  renderDuplicateGroups(summary.duplicateGroups);
  renderCharts(summary);
  resultsSection.classList.remove("hidden");
}

function buildDownloadBlob(fileName, headers, rows) {
  const extension = fileName.split(".").pop().toLowerCase();

  if (extension === "csv") {
    const csv = Papa.unparse(rows, { columns: headers });
    return {
      blob: new Blob([csv], { type: "text/csv;charset=utf-8;" }),
      fileName: fileName.replace(/\.[^.]+$/, "") + "_deduplicated.csv",
    };
  }

  const worksheet = XLSX.utils.json_to_sheet(rows, { header: headers });
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "CleanedData");
  const workbookArray = XLSX.write(workbook, { bookType: "xlsx", type: "array" });

  return {
    blob: new Blob([workbookArray], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }),
    fileName: fileName.replace(/\.[^.]+$/, "") + "_deduplicated.xlsx",
  };
}

processButton.addEventListener("click", async () => {
  resetMessages();
  resultsSection.classList.add("hidden");
  destroyCharts();
  currentResult = null;

  const file = fileInput.files[0];
  if (!file) {
    showMessage("error", "Please choose a CSV or Excel file first.");
    return;
  }

  try {
    const { headers, rows } = await parseFile(file);
    const summary = processRows(headers, rows);
    currentResult = {
      sourceFileName: file.name,
      headers,
      cleanedRows: summary.cleanedRows,
    };

    updateSummary(summary, file.name);
    showMessage("success", "File processed successfully.");
    if (file.name.toLowerCase().endsWith(".xls")) {
      showMessage("notice", "Legacy .xls files are exported as .xlsx after cleanup for better compatibility.");
    }
  } catch (error) {
    showMessage("error", `Could not process this file. ${error.message || error}`);
  }
});

downloadButton.addEventListener("click", () => {
  if (!currentResult) {
    showMessage("error", "Process a file before downloading the cleaned result.");
    return;
  }

  const payload = buildDownloadBlob(
    currentResult.sourceFileName,
    currentResult.headers,
    currentResult.cleanedRows,
  );

  const url = URL.createObjectURL(payload.blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = payload.fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});
