# Documentation claim auditor

An offline static auditor comparing documentation promises with listed source patterns. It inspects root README.md and Markdown under a docs path component. It parses source without executing it and uses no network, telemetry, or writes.

## Usage

```sh
python3 -m pip install .
spreadsheet-reading-claim-audit audit . --json
python3 -m spreadsheet_reading_claim_audit audit . --verbose
spreadsheet-reading-claim-audit audit . --fail-on medium --ignore vendor --ignore generated
spreadsheet-reading-claim-audit --version
```

The audit subcommand defaults to the current directory. Each ignore option accepts one relative path prefix. The default threshold is high; medium also fails on test-only findings. Exit codes are 0 for PASS, 2 for findings meeting the threshold, and 1 for usage or I/O errors. A PASS can contain a medium finding. JSON contains verdict, findings with rule, severity, message and locations, plus production_evidence, test_evidence, claims and denials.

## Matching

Blank lines delimit paragraphs. Backtick and tilde fences with up to three leading spaces are excluded; inline code counts. Text is lowercased, contractions expanded, hyphens replaced with spaces, and whitespace collapsed. Exact phrases match at word boundaries, longest first with alphabetical ties. Denial spans are removed before positive matching. There is at most one finding per claim family.

Only listed calls within a single module count. Import aliases resolve; local definitions and bindings shadow names. Syntax-invalid files and symlinks provide no evidence. Files under fixtures, docs and examples are excluded; tests are tracked separately. A positive statement without source fails; a denial without source passes.

```text
documented-spreadsheet-reading-claim-false HIGH (MEDIUM when evidence is test-only)
documented-no-spreadsheet-reading-claim-false HIGH
```

## Differentiation

The checked capability concerns existing workbook files. Workbook creation, document extraction and cloud sheet operations are separate capabilities and do not count. The exact vocabulary and accepted routes follow.

```text


SPREADSHEETREADING (50, one per line):
spreadsheet reading
read spreadsheet
reads spreadsheet
reading spreadsheet
read spreadsheets
reads spreadsheets
reading spreadsheets
load spreadsheet
loads spreadsheet
loading spreadsheet
load spreadsheets
loads spreadsheets
loading spreadsheets
open spreadsheet
opens spreadsheet
opening spreadsheet
open spreadsheets
opens spreadsheets
opening spreadsheets
parse spreadsheet
parses spreadsheet
parsing spreadsheet
parse spreadsheets
parses spreadsheets
parsing spreadsheets
import spreadsheet
imports spreadsheet
importing spreadsheet
import spreadsheets
imports spreadsheets
importing spreadsheets
spreadsheet reader
spreadsheet parser
spreadsheet importer
spreadsheet loading
read excel
reads excel
reading excel
read excel file
reads excel file
load excel
loads excel
loading excel
open excel
opens excel
opening excel
read xlsx
reads xlsx
read xls
load workbook

NOSPREADSHEETREADING (24, one per line):
no spreadsheet reading
does not read spreadsheet
does not read spreadsheets
does not support spreadsheet reading
without spreadsheet reading
no spreadsheet reader
does not load spreadsheet
does not load spreadsheets
does not open spreadsheet
does not open spreadsheets
does not parse spreadsheet
does not parse spreadsheets
does not import spreadsheet
does not import spreadsheets
no spreadsheet parser
does not read excel
does not read excel file
does not load excel
does not open excel
does not read xlsx
does not read xls
does not load workbook
spreadsheet reading not supported
no spreadsheet reading support

## Generic names (implementation MUST match exactly, 24, no duplicates)

read_spreadsheet, read_spreadsheets, load_spreadsheet, load_spreadsheets, open_spreadsheet, open_spreadsheets, parse_spreadsheet, parse_spreadsheets, import_spreadsheet, import_spreadsheets, read_excel, read_excel_file, load_excel, open_excel, read_xlsx, read_xls, read_workbook, load_workbook, open_workbook, read_excel_sheet, load_excel_file, parse_excel, parse_xlsx, spreadsheet_reader

## Library routes (implementation MUST match exactly)

- openpyxl load_workbook: a Call whose func is a Name resolved by
  from-import / aliased import to openpyxl.load_workbook, or an
  Attribute with attr exactly load_workbook whose value chain starts
  from a Name bound to openpyxl. Verified live in openpyxl 3.1.2
  2026-11-19: openpyxl.load_workbook(filename, read_only=False,
  keep_vba=False, data_only=False, keep_links=True,
  rich_text=False).
- xlrd open_workbook: a Call whose func is a Name resolved by
  from-import / aliased import to xlrd.open_workbook, or an
  Attribute with attr exactly open_workbook whose value chain starts
  from a Name bound to xlrd. Verified in the xlrd 2.0.2 wheel
  2026-11-19: xlrd/__init__.py defines
  `def open_workbook(filename=None, ...)` and re-exports
  open_workbook_xls from .book.
- pandas read_excel: a Call whose func is a Name resolved by
  from-import / aliased import to pandas.read_excel, or an Attribute
  with attr exactly read_excel whose value chain starts from a Name
  bound to pandas or to pd. Verified live in pandas 2.1.4
  2026-11-19: pandas.read_excel(io, sheet_name=0, ...) returning
  DataFrame | dict.
- odfpy load: a Call whose func is a Name resolved by a from-import /
  aliased import to odf.opendocument.load, or an Attribute with attr
  exactly load whose value chain starts from a Name bound to odf or
  to odf.opendocument. Verified in the odfpy 1.4.1 sdist 2026-11-19:
  odf/opendocument.py defines `def load(` (and
  `def OpenDocumentSpreadsheet()`).
- pyexcel get_book / get_records / get_sheet: a Call whose func is a
  Name resolved by a from-import / aliased import to
  pyexcel.get_book, pyexcel.get_records, or pyexcel.get_sheet, or
  an Attribute with attr exactly one of get_book, get_records,
  get_sheet whose value chain starts from a Name bound to pyexcel.
  Verified in the pyexcel 0.7.3 wheel 2026-11-19:
  pyexcel/__init__.py defines get_book, get_records, get_sheet
  (and get_array, deliberately NOT a listed route).


```

## Limitations

Static patterns are not semantic proof. Dead code counts and unresolved alias chains are missed. Detailed limitations follow.

```text


- The bare phrases "spreadsheet reading" / "read spreadsheet" /
  "load spreadsheet" / "open spreadsheet" / "parse spreadsheet" /
  "import spreadsheet" are deliberately SPREADSHEETREADING phrases:
  in document-tool docs they almost always name spreadsheet
  reading. But "open spreadsheet" can also name opening the Excel
  application (not a file), and "import spreadsheet" can name a
  menu item that merely copies an already-read workbook into a
  database: a doc that means the application or the import step,
  not file reading, is a false positive; the tool flags the claim,
  only the code decides.
- "read excel" / "load excel" / "open excel" phrases are
  deliberately phrases: a doc can say "read excel" about a tool
  that shells out to LibreOffice, which the tool deliberately does
  NOT detect (subprocess is NOT evidence). The tool flags the
  claim; only the code decides — and a subprocess-only codebase
  will be flagged HIGH, by design.
- "read xlsx" / "read xls" phrases are deliberately phrases: a doc
  can say "read xlsx" about a tool that only lists .xlsx filenames
  without opening them. The tool flags the claim; only the code
  decides.
- "load workbook" is deliberately a phrase: a doc can say "load
  workbook" about loading a workbook object that was already
  constructed in memory, with no file read in the repo. The tool
  flags the claim; only the code decides.
- "spreadsheet reader" / "spreadsheet parser" / "spreadsheet
  importer" are deliberately phrases: "spreadsheet reader" can
  also name a class that only wraps a spreadsheet writer, or a job
  title in prose. The tool flags the claim; only the code decides.
- An openpyxl load_workbook call with no sheet access in the module
  IS detected: the call itself is the read fingerprint; whether
  the code then reads any cell is not tracked. Say so in the README.
- An xlrd open_workbook call IS detected even though xlrd 2.0.2
  reads .xls only, not .xlsx: the tool detects the call, not
  whether the file opens. Say so in the README.
- A bare `x.load(...)` call on a name NOT bound to odf /
  odf.opendocument is NOT detected: `load` alone is too generic a
  method name to count unscoped. Say so in the README.
- A pyexcel get_array call is NOT detected: it reads any tabular
  source including CSV. Say so in the README.
- A pandas read_csv / csv module reader call is NOT detected: CSV
  is plain text, not a workbook. Say so in the README.
- A pandas ExcelFile construction with no read_excel / parse call
  in the module is NOT detected: the read happens via read_excel /
  parse, not via the constructor itself. Say so in the README.
- A tablib Dataset.load call is NOT detected: it is not a listed
  route this round. Say so in the README.
- gspread / pygsheets calls are NOT detected: they read cloud
  sheets, not files. Say so in the README.
- LibreOffice / UNO subprocess calls are NOT detected: shelling out
  to an external binary is NOT evidence by design. Say so in the
  README.
- Reading .txt / .html / .md / image files is NOT detected: reading
  a non-spreadsheet file is not reading a spreadsheet. Say so in
  the README.
- pypdf / PyPDF2 / pdfplumber / PyMuPDF text extraction is NOT
  detected: reading a PDF is not reading a spreadsheet. Say so in
  the README.
- python-docx Document opens are NOT detected: reading a Word
  document is not reading a spreadsheet. Say so in the README.
- python-pptx Presentation opens are NOT detected: reading a
  presentation is not reading a spreadsheet. Say so in the README.
- Spreadsheet writing (openpyxl / xlwt / pyexcelerate Workbook +
  save, XlsxWriter Workbook + close, odfpy OpenDocumentSpreadsheet
  + save, pandas DataFrame + to_excel) is NOT detected: writing a
  spreadsheet is not reading one. Say so in the README.
- Mindee parse with ANY product is NOT detected: mindee extracts
  from documents; it never reads workbooks. Say so in the README.
- Azure begin_analyze_document with ANY model id is NOT detected:
  Document Intelligence reads documents; it has no spreadsheet
  reading operation. Say so in the README.
- Veryfi calls of ANY kind are NOT detected: veryfi extracts fields
  from documents; it has no spreadsheet reading method. Say so in
  the README.
- Google Document AI process_document / batch_process_documents
  with ANY processor is NOT detected: Document AI has no
  spreadsheet reading processor. Say so in the README.
- Eden AI universal-ai calls with ANY model id are NOT detected:
  Eden AI documents no spreadsheet reading model. Say so in the
  README.
- Textract calls of ANY kind are NOT detected: Textract reads
  documents; it has no spreadsheet reading operation. Say so in
  the README.
- LlamaParse calls are NOT detected: its parsing API reads
  documents; it has no spreadsheet reading operation. Say so in
  the README.
- Nanonets / Docsumo / ABBYY Vantage / Rossum / Klippa / Parseur /
  Extend calls are NOT detected: opaque model / skill / queue /
  template / workflow IDs, or a generic upload endpoint with the
  document type configured outside the call — all extraction-side,
  no fixed fingerprint. Say so in the README.
- A hand-rolled spreadsheet reader built on raw OOXML / ZIP XML
  parsing (unzipping .xlsx and parsing sheet XML by hand, no
  listed call) is NOT detected: the tool requires a listed call.
  Say so in the README.
- Spreadsheet generation claims ("generate spreadsheet",
  "spreadsheet generation"), PDF generation claims ("generate pdf",
  "pdf generation"), invoice extraction claims ("extract invoices",
  "invoice extraction"), receipt extraction claims ("extract
  receipts", "receipt extraction"), ID document extraction claims
  ("extract passports", "passport extraction"), bank check
  extraction claims ("extract bank checks", "check extraction"),
  bank statement extraction claims ("extract bank statements",
  "statement extraction"), tax form extraction claims ("extract tax
  forms", "extract w2 forms", "1099 extraction"), pay stub
  extraction claims ("extract pay stubs", "payslip extraction"),
  health insurance card extraction claims ("extract health
  insurance cards", "health insurance card extraction"), business
  card extraction claims ("extract business cards", "business card
  extraction"), credit card extraction claims ("extract credit
  cards", "credit card extraction"), contract extraction claims
  ("extract contracts", "contract extraction"), mortgage extraction
  claims ("extract mortgages", "mortgage extraction"), resume
  extraction claims ("extract resumes", "resume extraction"), bill
  of lading extraction claims ("extract bills of lading", "bill of
  lading extraction"), delivery note extraction claims ("extract
  delivery notes", "delivery note extraction"), carte grise
  extraction claims ("extract carte grises", "carte grise
  extraction"), energy bill extraction claims ("extract energy
  bills", "energy bill extraction"), marriage certificate
  extraction claims ("extract marriage certificates", "marriage
  certificate extraction"), bank account details extraction claims
  ("extract bank account details", "bank account details
  extraction"), nutrition facts label extraction claims ("extract
  nutrition facts labels", "nutrition facts label extraction"),
  material certificate extraction claims ("extract material
  certificates", "material certificate extraction"), US mail
  extraction claims ("extract us mail", "us mail extraction"),
  invoice splitter claims ("split invoices", "invoice splitting"),
  multi-receipts detection claims ("detect multiple receipts",
  "multi receipt detection"), French health card extraction claims
  ("extract carte vitales", "french health card extraction"),
  Indian passport extraction claims ("extract indian passports",
  "indian passport extraction"), driver license extraction claims
  ("extract driver licenses", "driver license extraction"),
  vaccination card extraction claims ("extract vaccination cards",
  "vaccination card extraction"), document cropping claims ("crop
  documents", "document cropping"), and e-signature claims ("signs
  documents", "electronic signature") are NOT in the phrase lists:
  this family covers spreadsheet reading only. Say so in the
  README.
- As with every family: static pattern matching, not semantic
  judgement; dead code counts; alias chains the tracer cannot follow
  are missed; exact phrases only, not semantics; denial handling
  depends on the denial phrase list; each route must sit in a single
  module.

```

## Development

```sh
python3 -m unittest discover
python3 -m build
```

Requires version 3.9 or later of the interpreter. Distributed under the MIT license.
