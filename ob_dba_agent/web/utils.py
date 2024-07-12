# brew install tesseract first
import pytesseract
import os
from PIL import Image
import zipfile
import tarfile
import uuid
from os import path


def download_file(path: str, filename: str) -> str:
    """
    download_file downloads a file from a URL to local path
    """
    pass


tar_mode_mapping = {
    "application/x-tar": "r",
    "application/gzip": "r:gz",
    "application/x-bzip2": "r:bz2",
    "application/x-xz": "r:xz",
}


def extract_bundle(file_path: str) -> str:
    """
    extract_bundle extracts the contents of a compressed file to a directory
    Support file types: zip, tar, gz, bz2, xz
    :param file_path: path to the compressed file
    :return: path to the extracted directory
    """
    file_ext = path.splitext(file_path)[1]
    file_name = path.basename(file_path)
    new_file_name = path.join("uploaded", str(uuid.uuid4()) + "-" + file_name)
    output_dir = file_path.join("uploaded", "extracted", file_name)
    if file_ext == ".zip":
        with zipfile.ZipFile(new_file_name, "r") as zip_ref:
            zip_ref.extractall(output_dir)
    elif file_ext in [
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
    ]:
        with tarfile.open(new_file_name, tar_mode_mapping[file_ext]) as tar:
            tar.extractall(output_dir)
    else:
        raise ValueError("Unsupported file type")

    return output_dir


# If you don't have tesseract executable in your PATH, include the following:
pytesseract.pytesseract.tesseract_cmd = os.environ.get(
    "TESSERACT_BIN_PATH", "/opt/homebrew/bin/tesseract"
)


def parse_image(image_path: str) -> str:
    """
    parse_image extracts text from an image
    """
    return pytesseract.image_to_string(Image.open(image_path))
