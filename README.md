# OceanBase DBA Agent

## Quick Start

```bash
brew install tesseract # for mac
apt-get install -y tesseract-ocr # for ubuntu

poetry install
poetry shell
fastapi run webapp/main.py
```

## Embedding Documents

```bash
poetry shell
python3 cli/cli.py # optional, list all available commands
python3 cli/cli.py correct_md_headings --doc_folder /path/to/doc_folder
python3 cli/cli.py embedding_docs --doc_folder /path/to/doc_folder --db_file /path/to/output_db_file
```