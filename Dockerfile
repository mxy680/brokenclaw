FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY brokenclaw/ brokenclaw/

RUN pip install --no-cache-dir .

EXPOSE 9000

CMD ["uvicorn", "brokenclaw.main:app", "--host", "0.0.0.0", "--port", "9000"]
