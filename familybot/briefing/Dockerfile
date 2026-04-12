FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY briefing.py config.py ./

# shared/ is mounted at runtime via docker-compose volume

CMD ["python", "briefing.py"]
