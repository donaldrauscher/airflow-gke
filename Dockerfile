FROM puckel/docker-airflow:1.9.0
COPY ./dags/* /usr/local/airflow/dags/
COPY requirements.txt .
