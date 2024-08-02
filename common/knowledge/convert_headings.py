import re
import os
import sys


def convert_headings(input_file_path, output_file_path=None):
    """
    convert_headings converts markdown headings from format === and ---
    to the standard format # and ## respectively.
    """
    pattern_headline_1 = re.compile(r"^(.*)\n(\=+)$", re.MULTILINE)
    pattern_headline_2 = re.compile(r"^(.*)\n(\-+)$", re.MULTILINE)

    with open(input_file_path, "r", encoding="utf-8") as file:
        content = file.read()

    content = pattern_headline_1.sub(r"# \1", content)
    content = pattern_headline_2.sub(r"## \1", content)

    with open(output_file_path or input_file_path, "w", encoding="utf-8") as file:
        file.write(content)


def walk_dir(dir_path):
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith(".md"):
                convert_headings(os.path.join(root, file))
        for dir in dirs:
            walk_dir(os.path.join(root, dir))
