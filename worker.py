#Code under a source-available license. See more info in LICENSE
#Author: Merlin Van Cranem 
#Contact: vancranemmerlin@gmail.com
#https://github.com/Lenchanteu
#Last modifications: 30/08/2026 by Merlin Van Cranem
from pdf_maker import convert_to_pdf
from docxtpl import DocxTemplate

def generate_report_job(job_id, data, template, output_docx, output_pdf, jobs):
    try:
        jobs[job_id]["status"] = "processing"

        doc = DocxTemplate(template)
        doc.render(data)
        doc.save(output_docx)

        convert_to_pdf(output_docx)

        jobs[job_id]["status"] = "done"
        jobs[job_id]["file"] = output_pdf   # 🔥 important

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)