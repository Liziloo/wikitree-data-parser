FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir flask pymupdf

EXPOSE 5000

CMD ["python", "-m", "wikitree_data_parser.backend.webapp"]
