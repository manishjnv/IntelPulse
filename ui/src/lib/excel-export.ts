/**
 * Client-side Excel export helper.
 *
 * Replaces xlsx@0.18.5, which is on the deprecated branch with an unpatched
 * prototype-pollution CVE (GHSA-4r6h-8v6p-xvw6). exceljs is actively
 * maintained and has no known prototype-pollution advisories.
 *
 * Dynamic `import("exceljs")` keeps the ~300KB library out of the initial
 * bundle — it is pulled in only when a user clicks an Export button.
 */

type Row = Record<string, string | number | boolean | null | undefined>;

const XLSX_MIME =
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

/** Build and download an .xlsx file from a flat row array. */
export async function exportToExcel(
  rows: Row[],
  sheetName: string,
  filename: string,
): Promise<void> {
  if (rows.length === 0) return;

  const ExcelJS = (await import("exceljs")).default;
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(sheetName);

  const keys = Object.keys(rows[0]);
  ws.columns = keys.map((key) => {
    const maxLen = Math.max(
      key.length,
      ...rows.map((r) => String(r[key] ?? "").length),
    );
    return { header: key, key, width: Math.min(maxLen + 2, 60) };
  });
  ws.addRows(rows);

  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], { type: XLSX_MIME });
  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.endsWith(".xlsx") ? filename : `${filename}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
