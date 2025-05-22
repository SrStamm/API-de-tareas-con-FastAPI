FROM python:3.12-alpine

WORKDIR /backend

COPY requeriments.txt .

RUN pip install --no-cache-dir -r requeriments.txt

COPY . /backend

CMD ["uvicorn", "main:app","--port", "8000", "--reload"]
