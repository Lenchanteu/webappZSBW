import tempfile, subprocess, os



def latex_to_pdf(latex_code):
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "document.tex")

        # Write LaTeX
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_code)

        # Compile
        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-output-directory",
                tmpdir,
                tex_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(result.stdout)

        pdf_path = os.path.join(tmpdir, "document.pdf")

        # Read PDF into memory before temp folder is deleted
        with open(pdf_path, "rb") as pdf:
            return pdf.read()
