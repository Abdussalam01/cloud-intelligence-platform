FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/

COPY detector/ ./detector/

CMD ["python", "-m", "detector.src.run_detection"]
