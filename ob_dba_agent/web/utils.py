# brew install tesseract first
# apt-get install tesseract-ocr
import pytesseract
import os
from PIL import Image
import zipfile
import tarfile
import uuid

import requests
import json
from urllib.parse import quote
import unittest

from os import path

DOWNLOAD_SAVE_FOLDER = os.environ.get("DOWNLOAD_SAVE_FOLDER", "./downloaded")
FORUM_API_KEY = os.environ.get("FORUM_API_KEY")
FORUM_API_USERNAME = os.environ.get("FORUM_BOT_NAME", "序风")
FORUM_URL = os.environ.get("FORUM_API_URL", "https://ask-pre.oceanbase.com")

os.makedirs(DOWNLOAD_SAVE_FOLDER, exist_ok=True)

from bs4 import BeautifulSoup


def extract_files_from_html(
    html: str, filter_uploads: bool = True
) -> dict[str, list[str]]:
    """
    extract_file_path_from_html extracts file path from HTML content
    """
    soup = BeautifulSoup(html, features="html.parser")
    files: list[str] = [a["href"] for a in soup.find_all("a", href=True)]
    images: list[str] = [img["src"] for img in soup.find_all("img", src=True)]

    if filter_uploads:
        files = [f for f in files if f.startswith("/uploads")]
        images = [i for i in images if i.startswith("/uploads")]

    return {"files": files, "images": images}


def download_file(path: str, filename: str) -> str:
    """
    download_file downloads a file from a URL to local path
    """
    url = FORUM_URL + quote(path)
    file_path = os.path.join(DOWNLOAD_SAVE_FOLDER, filename)
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        return file_path
    else:
        return None


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
    output_dir = path.join("uploaded", "extracted", file_name)
    if file_ext == ".zip":
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)
    elif file_ext in [
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
    ]:
        with tarfile.open(file_path, tar_mode_mapping[file_ext]) as tar:
            tar.extractall(output_dir)
    else:
        raise ValueError("Unsupported file type")

    return output_dir


# If you don't have tesseract executable in your PATH, include the following:
pytesseract.pytesseract.tesseract_cmd = os.environ.get(
    "TESSERACT_BIN_PATH", "/usr/bin/tesseract"
)


def parse_image(image_path: str) -> str:
    """
    parse_image extracts text from an image
    """
    return pytesseract.image_to_string(Image.open(image_path))


def reply_post(topic_id: int, raw: str) -> int:
    """
    reply_post creates a new post in a topic
    @param topic_id: ID of the topic to reply to
    @param raw: raw content of the post, more than five words
    """
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json; charset=UTF-8",
        "Api-Key": FORUM_API_KEY,  # api key with at least topic write permission
        "Api-Username": quote(FORUM_API_USERNAME, encoding="utf-8"),
    }
    payload = json.dumps(
        {
            "raw": raw,
            "topic_id": topic_id,
        }
    )
    url = f"{FORUM_URL}/posts.json"
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.status_code


class TestUtils(unittest.TestCase):

    def test_parse_html(self):
        html = """
        <a href="/uploads/short-url/9tTa9jBId28YZhCDwQOB9Y6svSX.log">log file</a>
        <img src="/uploads/default/original/2X/5/5c9d30f4b15c36e9cb76e2e7309e16c39322d8ec.png">
        """
        files = extract_files_from_html(html)
        self.assertEqual(
            files,
            {
                "files": ["/uploads/short-url/9tTa9jBId28YZhCDwQOB9Y6svSX.log"],
                "images": [
                    "/uploads/default/original/2X/5/5c9d30f4b15c36e9cb76e2e7309e16c39322d8ec.png"
                ],
            },
        )

    def test_download_file(self):
        path = "/uploads/short-url/9tTa9jBId28YZhCDwQOB9Y6svSX.log"
        filename = os.path.basename(path)
        downloaded_file = download_file(path, filename)
        os.path.exists(downloaded_file)

    def test_reply_post(self):
        topic_id = 35604704
        raw = "Hello, world!"
        response = reply_post(topic_id, raw)
        self.assertEqual(response, 200)


if __name__ == "__main__":
    unittest.main()
