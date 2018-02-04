import requests, json

from collections import OrderedDict
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import BaseOperator
from airflow.hooks import BigQueryHook
from airflow.utils.decorators import apply_defaults


default_args = {
    'owner': 'airflow',
    'retries': 2,
    'retry_delay': timedelta(minutes = 1)
}

dag = DAG('citibike',
    start_date = datetime(2018, 1, 28),
    schedule_interval = '*/5 * * * *',
    catchup = False,
    default_args = default_args)

class StationStatus(BaseOperator):

    _schema = [
        ('station_id', {'field_type':'STRING'}),
        ('num_bikes_available', {'field_type':'INTEGER'}),
        ('num_bikes_disabled', {'field_type':'INTEGER'}),
        ('num_docks_available', {'field_type':'INTEGER'}),
        ('num_docks_disabled', {'field_type':'INTEGER'}),
        ('is_installed', {'field_type':'INTEGER'}),
        ('is_renting', {'field_type':'INTEGER'}),
        ('is_returning', {'field_type':'INTEGER'}),
        ('last_reported', {'field_type':'INTEGER'}),
        ('eightd_has_available_keys', {'field_type':'BOOLEAN'}),
        ('timestamp', {'field_type':'DATETIME'})
    ]

    @apply_defaults
    def __init__(self, conn_id = "google_cloud_default", *args, **kwargs):
        super(StationStatus, self).__init__(*args, **kwargs)
        self.conn_id = conn_id

    def execute(self, context):

        # fetch data
        req = requests.get('https://gbfs.citibikenyc.com/gbfs/en/station_status.json')
        data = json.loads(req.text, object_pairs_hook=OrderedDict)
        data = data['data']['stations']

        # add timestamps
        ts = datetime.now()
        for x in data:
            x.update(timestamp=ts)

        # stream into BigQuery
        rows = [tuple(x.values()) for x in data]
        hook = BigQueryHook(conn_id = self.conn_id)
        hook.insert_rows('citibike', 'station_status', rows, self._schema)


t1 = StationStatus(task_id = 'station_status', dag = dag)
