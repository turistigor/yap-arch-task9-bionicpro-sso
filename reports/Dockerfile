FROM python:3.12-slim as auth_builder

WORKDIR /opt/app/reports
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

EXPOSE 8001
CMD python -m src
