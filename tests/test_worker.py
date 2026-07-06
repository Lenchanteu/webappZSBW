import importlib
import sys
import types


def test_generate_report_job_marks_job_as_done(monkeypatch):
    fake_docxtpl = types.ModuleType("docxtpl")

    class FakeDocxTemplate:
        def __init__(self, template):
            self.template = template

        def render(self, data):
            self.data = data

        def save(self, output):
            self.output = output

    fake_docxtpl.DocxTemplate = FakeDocxTemplate
    sys.modules["docxtpl"] = fake_docxtpl

    fake_pdf_maker = types.ModuleType("pdf_maker")
    fake_pdf_maker.convert_to_pdf = lambda path: None
    sys.modules["pdf_maker"] = fake_pdf_maker

    sys.modules.pop("worker", None)
    worker = importlib.import_module("worker")

    jobs = {"job-1": {"status": "queued"}}
    worker.generate_report_job("job-1", {"name": "demo"}, "template.docx", "out.docx", "out.pdf", jobs)

    assert jobs["job-1"]["status"] == "done"
    assert jobs["job-1"]["file"] == "out.pdf"
