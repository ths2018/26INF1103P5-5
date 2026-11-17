FROM python:3.12-slim

WORKDIR /app

COPY ["Project Code/requirements.txt", "requirements.txt"]

RUN pip install --no-cache-dir -r requirements.txt

COPY ["Project Code/", "."]

CMD ["python", "main.py"]
