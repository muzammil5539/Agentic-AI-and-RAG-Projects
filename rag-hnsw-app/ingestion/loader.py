from pathlib import Path
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    CSVLoader,
)

LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".docx": Docx2txtLoader,
    ".csv": CSVLoader,
}


def load_document(file_path: str) -> list:
    ext = Path(file_path).suffix.lower()
    loader_cls = LOADER_MAP.get(ext)
    if loader_cls is None:
        raise ValueError(f"Unsupported file type: {ext}")

    loader = loader_cls(file_path)
    docs = loader.load()

    for i, doc in enumerate(docs):
        doc.metadata["source_filename"] = Path(file_path).name
        if "page" not in doc.metadata:
            doc.metadata["page"] = i + 1

    return docs
