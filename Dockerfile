FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY pkg pkg
COPY bin bin
CMD ["uvicorn", "bin.server:app", "--host", "0.0.0.0"]
