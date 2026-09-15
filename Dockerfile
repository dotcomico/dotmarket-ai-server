FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8100

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8100"]
