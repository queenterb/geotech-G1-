FROM python:3.11-slim

WORKDIR /opt
COPY cis/ /opt/cis/

RUN pip install --no-cache-dir -r /opt/cis/requirements.txt

CMD ["python", "-m", "cis.service"]
