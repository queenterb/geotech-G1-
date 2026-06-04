FROM python:3.11-slim

WORKDIR /opt/cis
COPY cis/ /opt/cis/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main_detector.py"]
