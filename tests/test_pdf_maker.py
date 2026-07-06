import importlib
import sys
import types


def test_pdf_maker_invokes_converter(monkeypatch):
    fake_pythoncom = types.ModuleType("pythoncom")
    fake_pythoncom.CoInitialize = lambda: None
    fake_pythoncom.CoUninitialize = lambda: None
    sys.modules["pythoncom"] = fake_pythoncom

    calls = []

    def fake_convert(path):
        calls.append(path)

    fake_docx2pdf = types.ModuleType("docx2pdf")
    fake_docx2pdf.convert = fake_convert
    sys.modules["docx2pdf"] = fake_docx2pdf

    sys.modules.pop("pdf_maker", None)
    pdf_maker = importlib.import_module("pdf_maker")

    pdf_maker.convert_to_pdf("sample.docx")

    assert calls == ["sample.docx"]
