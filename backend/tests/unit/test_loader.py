import os
import tempfile
import pytest
import numpy as np
from PIL import Image
import fitz

from app.modules.acquisition.loader import DocumentLoader, DocumentLoadingError

def create_temp_image(filename: str, color=(200, 200, 200), size=(200, 100)) -> str:
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, filename)
    img = Image.new("RGB", size, color=color)
    img.save(path)
    return path

def create_temp_pdf(filename: str) -> str:
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, filename)
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.insert_text((50, 50), "Sample Synthetic PDF Document")
    doc.save(path)
    doc.close()
    return path

def test_load_jpg():
    path = create_temp_image("test_sample.jpg")
    try:
        pages = DocumentLoader.load_pages_rgb(path)
        assert len(pages) == 1
        assert isinstance(pages[0], np.ndarray)
        assert pages[0].shape == (100, 200, 3)
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_load_png():
    path = create_temp_image("test_sample.png")
    try:
        pages = DocumentLoader.load_pages_rgb(path)
        assert len(pages) == 1
        assert pages[0].shape == (100, 200, 3)
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_load_webp():
    path = create_temp_image("test_sample.webp")
    try:
        pages = DocumentLoader.load_pages_rgb(path)
        assert len(pages) == 1
        assert pages[0].shape == (100, 200, 3)
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_load_tiff():
    path = create_temp_image("test_sample.tiff")
    try:
        pages = DocumentLoader.load_pages_rgb(path)
        assert len(pages) == 1
        assert pages[0].shape == (100, 200, 3)
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_load_pdf():
    path = create_temp_pdf("test_sample.pdf")
    try:
        pages = DocumentLoader.load_pages_rgb(path, dpi=72)
        assert len(pages) == 1
        assert isinstance(pages[0], np.ndarray)
        assert pages[0].shape[0] == 400
        assert pages[0].shape[1] == 300
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_load_non_existent_file():
    with pytest.raises(DocumentLoadingError) as exc_info:
        DocumentLoader.load_pages_rgb("non_existent_file_path_xyz.jpg")
    assert "File does not exist" in str(exc_info.value)

def test_load_empty_file():
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, "empty_file.jpg")
    with open(path, "wb") as f:
        pass  # 0 bytes
    try:
        with pytest.raises(DocumentLoadingError) as exc_info:
            DocumentLoader.load_pages_rgb(path)
        assert "File is empty" in str(exc_info.value)
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_load_corrupted_image():
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, "corrupt_image.png")
    with open(path, "wb") as f:
        f.write(b"this is not a valid image format payload data")
    try:
        with pytest.raises(DocumentLoadingError):
            DocumentLoader.load_pages_rgb(path)
    finally:
        if os.path.exists(path):
            os.remove(path)
