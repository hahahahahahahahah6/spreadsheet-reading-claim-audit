import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from spreadsheet_reading_claim_audit.audit import audit, evidence, paragraphs, matches, normalize
from spreadsheet_reading_claim_audit import phrases
from spreadsheet_reading_claim_audit.__main__ import main

EXPECTED_YES = ('spreadsheet reading', 'read spreadsheet', 'reads spreadsheet', 'reading spreadsheet', 'read spreadsheets', 'reads spreadsheets', 'reading spreadsheets', 'load spreadsheet', 'loads spreadsheet', 'loading spreadsheet', 'load spreadsheets', 'loads spreadsheets', 'loading spreadsheets', 'open spreadsheet', 'opens spreadsheet', 'opening spreadsheet', 'open spreadsheets', 'opens spreadsheets', 'opening spreadsheets', 'parse spreadsheet', 'parses spreadsheet', 'parsing spreadsheet', 'parse spreadsheets', 'parses spreadsheets', 'parsing spreadsheets', 'import spreadsheet', 'imports spreadsheet', 'importing spreadsheet', 'import spreadsheets', 'imports spreadsheets', 'importing spreadsheets', 'spreadsheet reader', 'spreadsheet parser', 'spreadsheet importer', 'spreadsheet loading', 'read excel', 'reads excel', 'reading excel', 'read excel file', 'reads excel file', 'load excel', 'loads excel', 'loading excel', 'open excel', 'opens excel', 'opening excel', 'read xlsx', 'reads xlsx', 'read xls', 'load workbook')
EXPECTED_NO = ('no spreadsheet reading', 'does not read spreadsheet', 'does not read spreadsheets', 'does not support spreadsheet reading', 'without spreadsheet reading', 'no spreadsheet reader', 'does not load spreadsheet', 'does not load spreadsheets', 'does not open spreadsheet', 'does not open spreadsheets', 'does not parse spreadsheet', 'does not parse spreadsheets', 'does not import spreadsheet', 'does not import spreadsheets', 'no spreadsheet parser', 'does not read excel', 'does not read excel file', 'does not load excel', 'does not open excel', 'does not read xlsx', 'does not read xls', 'does not load workbook', 'spreadsheet reading not supported', 'no spreadsheet reading support')
EXPECTED_GENERIC = ('read_spreadsheet', 'read_spreadsheets', 'load_spreadsheet', 'load_spreadsheets', 'open_spreadsheet', 'open_spreadsheets', 'parse_spreadsheet', 'parse_spreadsheets', 'import_spreadsheet', 'import_spreadsheets', 'read_excel', 'read_excel_file', 'load_excel', 'open_excel', 'read_xlsx', 'read_xls', 'read_workbook', 'load_workbook', 'open_workbook', 'read_excel_sheet', 'load_excel_file', 'parse_excel', 'parse_xlsx', 'spreadsheet_reader')


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = main(list(args))
            except SystemExit as error:
                code = error.code
        return code, output.getvalue()

    def test_phrase_oracle(self):
        parsed = ast.parse(Path(phrases.__file__).read_text())
        values = {n.targets[0].id: ast.literal_eval(n.value) for n in parsed.body if isinstance(n, ast.Assign)}
        for key, expected in [('SPREADSHEETREADING', EXPECTED_YES), ('NOSPREADSHEETREADING', EXPECTED_NO), ('GENERIC_NAMES', EXPECTED_GENERIC)]:
            self.assertEqual(values[key], expected)
            self.assertEqual(len(values[key]), len(set(values[key])))
        self.assertEqual(len(EXPECTED_YES), 50)
        self.assertEqual(len(EXPECTED_NO), 24)
        self.assertEqual(len(EXPECTED_GENERIC), 24)

    def test_good(self):
        self.put('README.md', 'We read spreadsheets.')
        self.put('app.py', 'from openpyxl import load_workbook\nload_workbook("in.xlsx")')
        self.assertEqual(audit(self.root)['verdict'], 'PASS')

    def test_bad(self):
        self.put('README.md', 'read spreadsheet')
        code, output = self.cli('audit', str(self.root), '--json')
        self.assertEqual(code, 2)
        result = json.loads(output)
        self.assertEqual(result['verdict'], 'FAIL')
        finding = result['findings'][0]
        self.assertEqual(finding['rule'], 'documented-spreadsheet-reading-claim-false')
        self.assertEqual(finding['severity'], 'HIGH')
        self.assertTrue(finding['message'])

    def test_test_only(self):
        self.put('README.md', 'read spreadsheet')
        self.put('tests/app.py', 'x.read_spreadsheet()')
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'MEDIUM')
        self.assertEqual(self.cli('audit', str(self.root))[0], 0)
        self.assertEqual(self.cli('audit', str(self.root), '--fail-on', 'medium')[0], 2)

    def test_denial(self):
        self.put('README.md', 'does not read spreadsheet')
        self.assertEqual(audit(self.root)['verdict'], 'PASS')
        self.put('app.py', 'x.read_spreadsheet()')
        result = audit(self.root)
        self.assertEqual(len(result['findings']), 1)
        self.assertEqual(result['findings'][0]['rule'], 'documented-no-spreadsheet-reading-claim-false')
        self.assertEqual(result['findings'][0]['severity'], 'HIGH')
        self.assertEqual(self.cli('audit', str(self.root))[0], 2)

    def test_no_claim(self):
        self.put('README.md', 'Ordinary utility')
        self.put('app.py', 'x.read_spreadsheet()')
        self.assertEqual(audit(self.root)['findings'], [])

    def test_fences_inline_and_paragraphs(self):
        self.put('README.md', '   ```text\nread spreadsheet\n   ```\n\n~~~\nread excel\n~~~')
        self.assertEqual(audit(self.root)['verdict'], 'PASS')
        self.put('README.md', '`read spreadsheet`')
        self.assertEqual(audit(self.root)['verdict'], 'FAIL')
        self.put('README.md', 'generate\n\nspreadsheet')
        self.assertEqual(audit(self.root)['verdict'], 'PASS')
        self.assertEqual(paragraphs('````\nread spreadsheet\n```\nread excel\n````'), [])

    def test_normalization_boundaries(self):
        self.assertEqual(normalize("DOESN'T read-spreadsheet"), 'does not read spreadsheet')
        self.assertFalse(matches('reread spreadsheetsx', EXPECTED_YES))
        self.put('README.md', "doesn't read-spreadsheet")
        self.assertEqual(audit(self.root)['claims'], [])
        self.assertEqual(matches('read excel file', EXPECTED_YES)[0].group(), 'read excel file')

    def test_split_modules(self):
        self.put('README.md', 'read spreadsheet')
        self.put('a.py', 'from odf.opendocument import load as reader')
        self.put('b.py', 'reader("in.ods")')
        self.assertEqual(audit(self.root)['verdict'], 'FAIL')

    def test_docs_and_excluded_paths(self):
        self.put('nested/docs/claims.md', 'read spreadsheet')
        for folder in ['fixtures', 'docs', 'examples']:
            self.put(folder + '/app.py', 'x.read_spreadsheet()')
        self.put('other.md', 'does not read spreadsheet')
        self.assertEqual(audit(self.root)['production_evidence'], [])
        self.assertEqual(audit(self.root)['denials'], [])
        self.assertEqual(audit(self.root)['verdict'], 'FAIL')

    def test_test_filename_patterns(self):
        for path in ['test_app.py', 'app_test.py', 'nested/tests/module.py']:
            self.put(path, 'x.read_spreadsheet()')
        result = audit(self.root)
        self.assertEqual(len(result['test_evidence']), 3)
        self.assertEqual(result['production_evidence'], [])

    def test_symlinks(self):
        self.put('fixtures/real.py', 'x.read_spreadsheet()')
        self.put('fixtures/README.md', 'read spreadsheet')
        (self.root/'app.py').symlink_to(self.root/'fixtures/real.py')
        (self.root/'README.md').symlink_to(self.root/'fixtures/README.md')
        (self.root/'linked').symlink_to(self.root/'fixtures', target_is_directory=True)
        self.assertEqual(audit(self.root)['production_evidence'], [])
        self.assertEqual(audit(self.root)['claims'], [])

    def test_ignore(self):
        self.put('README.md', 'read spreadsheet')
        self.put('vendor/app.py', 'x.read_spreadsheet()')
        self.assertEqual(audit(self.root, ['vendor'])['verdict'], 'FAIL')
        self.assertEqual(self.cli('audit', str(self.root), '--ignore', 'vendor', '--ignore', 'README')[0], 0)

    def test_usage_errors_and_version(self):
        for args in [[], ['wrong'], ['audit', '--fail-on', 'HIGH'], ['audit', '--ignore', 'one', 'two', 'three'], ['audit', str(self.root/'missing')]]:
            self.assertEqual(self.cli(*args)[0], 1)
        self.assertEqual(self.cli('--version'), (0, '0.1.0\n'))
        self.assertEqual(subprocess.run([sys.executable, '-m', 'spreadsheet_reading_claim_audit', '--version'], capture_output=True, text=True).stdout, '0.1.0\n')

    def test_readme_self_audit(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(audit(root)['findings'], [])
        for paragraph in paragraphs((root/'README.md').read_text()):
            self.assertFalse(matches(paragraph, EXPECTED_YES + EXPECTED_NO))


def add_case(name, source, expected):
    def test(self):
        self.assertEqual(evidence(source), expected, source)
    setattr(AuditTests, 'test_' + name, test)

for index, phrase in enumerate(EXPECTED_YES):
    def positive(self, phrase=phrase):
        self.put('README.md', phrase)
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'HIGH')
    setattr(AuditTests, 'test_positive_phrase_%02d' % index, positive)
for index, phrase in enumerate(EXPECTED_NO):
    def negative(self, phrase=phrase):
        self.put('README.md', phrase)
        result = audit(self.root)
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['verdict'], 'PASS')
        self.put('app.py', 'x.read_spreadsheet()')
        self.assertEqual(len(audit(self.root)['findings']), 1)
    setattr(AuditTests, 'test_negative_phrase_%02d' % index, negative)
for name in EXPECTED_GENERIC:
    add_case('generic_attr_' + name, 'obj.' + name + '()', True)
    add_case('generic_import_' + name, 'from utility import ' + name + ' as call\ncall()', True)
    add_case('generic_bare_' + name, name + '()', False)
    add_case('generic_shadow_' + name, 'def ' + name + '(): pass\nobj.' + name + '()', False)


ROUTES = [('openpyxl', 'load_workbook'), ('xlrd', 'open_workbook'), ('pandas', 'read_excel'), ('odf.opendocument', 'load'), ('pyexcel', 'get_book'), ('pyexcel', 'get_records'), ('pyexcel', 'get_sheet')]
for lib, method in ROUTES:
    key = lib.replace('.', '_') + '_' + method
    for i, source in enumerate([
        'from %s import %s\n%s()' % (lib, method, method),
        'from %s import %s as call\ncall()' % (lib, method),
        'import %s as lib\nlib.%s()' % (lib, method),
        'import %s\n%s.%s()' % (lib, lib, method),
    ]):
        add_case(key + '_form_' + str(i), source, True)
    if method not in EXPECTED_GENERIC:
        for i, binding in enumerate(['lib = fake', 'lib: object = fake', 'with ctx() as lib: pass', 'async def f():\n async with ctx() as lib: pass']):
            add_case(key + '_bound_' + str(i), 'import %s as lib\n%s\nlib.%s()' % (lib, binding, method), False)
    add_case(key + '_shadow', 'from %s import %s\ndef %s(): pass\n%s()' % (lib, method, method, method), False)
add_case('odf_from_module', 'from odf import opendocument as od\nod.load()', True)
add_case('pandas_pd', 'import pandas as pd\npd.read_excel()', True)
NOT_EVIDENCE = [
'import openpyxl', 'import xlrd', 'import pandas', 'import odf', 'import pyexcel', 'import csv',
'import openpyxl\nopenpyxl.Workbook().save("x")', 'import xlwt\nxlwt.Workbook().save("x")',
'import xlsxwriter\nxlsxwriter.Workbook().close()', 'from odf.opendocument import OpenDocumentSpreadsheet\nOpenDocumentSpreadsheet().save("x")',
'import pandas\npandas.DataFrame().to_excel("x")', 'import pandas as pd\npd.read_csv("x")',
'import csv\ncsv.reader(f)', 'import csv\ncsv.DictReader(f)', 'import pandas\npandas.ExcelFile("x")',
'import tablib\ntablib.Dataset().load(data)', 'import pyexcel\npyexcel.get_array(file_name="x")',
'import gspread\ngspread.open("book")', 'import pygsheets\npygsheets.authorize()',
'import subprocess\nsubprocess.run(["libreoffice"])', 'open("x.txt").read()', 'Path("x.md").read_text()',
'Image.open("x.png")', 'pypdf.PdfReader(f).pages[0].extract_text()', 'pdfplumber.open(f).pages[0].extract_text()',
'docx.Document("x.docx")', 'pptx.Presentation("x.pptx")', '"spreadsheet xlsx Excel"', 'x.load(f)',
'mindee.parse(InvoiceV4, f)', 'azure.begin_analyze_document("prebuilt-layout", f)', 'veryfi.Client()',
'documentai.process_document(request)', 'textract.analyze_document(Document=data)', 'eden.universal_ai(model="anything")',
'LlamaParse().load_data(f)', 'nanonets.OCR(model_id="opaque")', 'docsumo.upload(f)', 'abbyy.run(skill="opaque")',
'rossum.upload(queue="opaque")', 'klippa.parse(f)', 'parseur.upload(f)', 'extend.run(workflow="opaque")',
'obj.read_spreadsheet', 'def broken(', 'from tools import read_spreadsheet as g\ng = other\ng()',
]
for i, source in enumerate(NOT_EVIDENCE):
    add_case('not_evidence_%02d' % i, source, False)

if __name__ == '__main__':
    unittest.main()
