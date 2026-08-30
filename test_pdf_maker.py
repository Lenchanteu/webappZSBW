from unittest.mock import patch

import pytest
import pdf_maker


@patch("pdf_maker.pythoncom.CoUninitialize")
@patch("pdf_maker.convert")
@patch("pdf_maker.pythoncom.CoInitialize")
def test_convert_to_pdf_error(
    mock_coinitialize,
    mock_convert,
    mock_couninitialize
):
    mock_convert.side_effect = RuntimeError("Conversion failed")

    with pytest.raises(RuntimeError, match="Conversion failed"):
        pdf_maker.convert_to_pdf("test_document.docx")

    mock_coinitialize.assert_called_once()
    mock_convert.assert_called_once_with("test_document.docx")

    # Even though conversion failed,
    # CoUninitialize must still be called.
    mock_couninitialize.assert_called_once()