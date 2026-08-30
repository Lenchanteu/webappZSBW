#Code under a source-available license. See more info in LICENSE
#Author: Merlin Van Cranem 
#Contact: vancranemmerlin@gmail.com
#https://github.com/Lenchanteu
#Last modifications: 30/08/2026 by Merlin Van Cranem
#--------------IMPORTS-------------------
import pythoncom
from docx2pdf import convert
#------------FUNCTION------------------
def convert_to_pdf(docx_file):
    pythoncom.CoInitialize()
    try:
        convert(docx_file)
    finally:
        pythoncom.CoUninitialize()


#FOR LINUX USE: 
#Comment all the code above, and uncomment the code bellow. 
#Make shure that LibreOffice is installed. The code bellow also works on windows with LibreOffice installed.
#-------------IMPORTS----------------
"""import subprocess
#-------------FUNCTION--------------
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
