#Code under a source-available license. See more info in LICENSE
#Author: Merlin Van Cranem 
#Contact: vancranemmerlin@gmail.com
#https://github.com/Lenchanteu
#Last modifications: 02/09/2026 by Merlin Van Cranem
from pdf_maker import convert_to_pdf
from docxtpl import DocxTemplate
from email_sender import send_PDF_to_people
import email_config
EMAILS = email_config.EMAILS

def generate_report_job(job_id, data, template, output_docx, output_pdf, jobs, commune, send_to_bourg):
    try:
        jobs[job_id]["status"] = "processing"

        doc = DocxTemplate(template)
        doc.render(data)
        doc.save(output_docx)

        convert_to_pdf(output_docx)

        if send_to_bourg:
            if not commune or commune not in EMAILS:
                raise Exception("User somehow entered a wrong commune in rapport generation.")
            
            email = EMAILS[commune]
            send_PDF_to_people(email, output_pdf)
        
        jobs[job_id]["status"] = "done"
        jobs[job_id]["file"] = output_pdf   # 🔥 important

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)