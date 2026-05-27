FROM apache/airflow:3.2.2-python3.11

COPY requirements.txt /requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r /requirements.txt

USER airflow
