
import pythoncom
from docx2pdf import convert
#import subprocess
def convert_to_pdf(docx_file):
    pythoncom.CoInitialize()
    try:
        convert(docx_file)
    finally:
        pythoncom.CoUninitialize()

"""Linux:
def convert_to_pdf(docx_file):
    
    Converts DOCX to PDF using LibreOffice.
    Works on Linux and Windows with LibreOffice installed.
    
    subprocess.run([
        "soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        ".",
        docx_file
    ], check=True)"""