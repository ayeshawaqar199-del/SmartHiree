"""Resume parsing strategies.

This module intentionally keeps file-format details outside the matching engine.
It demonstrates the Strategy pattern (one parser per format) and the Factory
pattern (select a parser from the uploaded file extension).
"""
from abc import ABC, abstractmethod
from os.path import splitext
from zipfile import ZipFile
import xml.etree.ElementTree as ET


MAX_RESUME_TEXT = 150_000
MAX_DOCX_XML_SIZE = 5 * 1024 * 1024
DOCX_TEXT_TAG = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"


class ResumeParseError(ValueError):
    """Raised when an uploaded CV cannot safely be converted to text."""


class ResumeParserStrategy(ABC):
    """Strategy interface shared by all supported resume parsers."""

    @abstractmethod
    def parse(self, upload):
        """Return the extracted text from an already-open uploaded file."""
        raise NotImplementedError

    def extract(self, upload):
        """Run the parser and restore the upload stream for later saving."""
        try:
            upload.seek(0)
            text = self.parse(upload)
        except ResumeParseError:
            raise
        except Exception as exc:
            raise ResumeParseError(
                "We couldn't read this CV. Try a text-based PDF or a valid DOCX file."
            ) from exc
        finally:
            try:
                upload.seek(0)
            except (AttributeError, OSError, ValueError):
                pass

        if not text or not str(text).strip():
            raise ResumeParseError(
                "No selectable text was found. Scanned PDFs need OCR; upload a text-based PDF or DOCX."
            )
        return str(text)[:MAX_RESUME_TEXT]


class PdfResumeParser(ResumeParserStrategy):
    """Strategy for extracting selectable text from PDF files."""

    def parse(self, upload):
        from pypdf import PdfReader

        reader = PdfReader(upload, strict=False)
        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")
            except Exception as exc:
                raise ResumeParseError(
                    "This PDF is password protected. Upload an unlocked copy."
                ) from exc
            if not decrypted:
                raise ResumeParseError(
                    "This PDF is password protected. Upload an unlocked copy."
                )

        return "\n".join(page.extract_text() or "" for page in reader.pages[:20])


class DocxResumeParser(ResumeParserStrategy):
    """Strategy for extracting text from the main Word document XML."""

    def parse(self, upload):
        with ZipFile(upload) as archive:
            try:
                document_info = archive.getinfo("word/document.xml")
            except KeyError as exc:
                raise ResumeParseError(
                    "This Word file is missing its document content. Upload a valid DOCX file."
                ) from exc

            if document_info.file_size > MAX_DOCX_XML_SIZE:
                raise ResumeParseError(
                    "This Word document expands beyond the supported size."
                )

            root = ET.fromstring(archive.read("word/document.xml"))

        return " ".join(node.text or "" for node in root.iter(DOCX_TEXT_TAG))


class ResumeParserFactory:
    """Factory that returns the correct Strategy for a filename extension."""

    _strategies = {
        ".pdf": PdfResumeParser,
        ".docx": DocxResumeParser,
    }

    @classmethod
    def create(cls, filename):
        extension = splitext(str(filename or ""))[1].casefold()
        strategy = cls._strategies.get(extension)
        if strategy is None:
            raise ResumeParseError(
                "Upload a PDF or DOCX file so SmartHire can read its skills."
            )
        return strategy()
