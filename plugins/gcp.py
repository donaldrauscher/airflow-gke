import json

from collections import OrderedDict

from airflow.hooks.base_hook import BaseHook
from airflow.plugins_manager import AirflowPlugin
from airflow.exceptions import AirflowException
from airflow.utils.log.logging_mixin import LoggingMixin

import google.auth
from google.auth import _cloud_sdk
from google.oauth2 import service_account

from google.cloud.bigquery import Client, Table, SchemaField


# my own GCP hook; uses google-auth since oauth2client was deprecated
class GoogleCloudBaseHook(BaseHook, LoggingMixin):

    def __init__(self, conn_id):
        self.conn_id = conn_id
        self.extras = self.get_connection(conn_id).extra_dejson

    @property
    def project_id(self):
        proj = self._get_field('project')
        if not proj:
            proj = _cloud_sdk.get_project_id()
        return proj

    def _get_credentials(self):
        key_path = self._get_field('key_path', False)
        keyfile_dict = self._get_field('keyfile_dict', False)
        scope = self._get_field('scope', False)

        if not key_path and not keyfile_dict:
            self.log.info('Getting connection using `gcloud auth` user, since no key file is defined for hook.')
            credentials, _ = google.auth.default()
        elif key_path:
            if not scope:
                raise AirflowException('Scope should be defined when using a key file.')
            scopes = [s.strip() for s in scope.split(',')]

            self.log.info('Getting connection using a JSON key file.')
            credentials = service_account.Credentials.from_service_account_file(key_path, scopes = scopes)
        else:
            if not scope:
                raise AirflowException('Scope should be defined when using JSON key.')
            scopes = [s.strip() for s in scope.split(',')]

            self.log.info('Getting connection using a JSON key.')
            keyfile_dict = json.loads(keyfile_dict)
            # depending on how the JSON was formatted, it may contain escaped newlines; onvert those to actual newlines
            keyfile_dict['private_key'] = keyfile_dict['private_key'].replace('\\n', '\n')
            credentials = service_account.Credentials.from_service_account_info(keyfile_dict, scopes = scopes)

        return credentials

    def _get_field(self, f, default = None):
        long_f = 'extra__google_cloud_platform__{}'.format(f)
        return self.extras.get(long_f, default)


# my BQ hook which uses google-cloud-bigquery
class BigQueryHook(GoogleCloudBaseHook):

    _client = None

    def __init__(self, conn_id = 'google_cloud_default'):
        super(BigQueryHook, self).__init__(conn_id = conn_id)

    @property
    def client(self):
        if not self._client:
            self._client = Client(project = self.project_id, credentials = self._get_credentials())
        return self._client

    @staticmethod
    def schema_object(schema):
        schema_object = []
        for k,v in OrderedDict(schema).items():
            field_type = v.get('field_type', 'STRING')
            mode = v.get('mode', 'REQUIRED')
            schema_object.append(SchemaField(k, field_type, mode))
        return schema_object

    def get_table(self, dataset_name, table_name, schema):
        dataset = self.client.dataset(dataset_name)
        dataset_table_names = [t.table_id for t in self.client.list_tables(dataset)]
        table_ref = dataset.table(table_name)
        if table_name not in dataset_table_names:
            assert schema
            table = Table(table_ref, self.schema_object(schema))
            table = self.client.create_table(table)
        else:
            table = self.client.get_table(table_ref)
        return table

    def insert_rows(self, dataset_name, table_name, rows, schema = None):
        table = self.get_table(dataset_name, table_name, schema)
        self.client.insert_rows(table, rows)


# wrap everything as a plugin
class GCPPlugin(AirflowPlugin):
    name = "GCP plugins using google-cloud-python"
    hooks = [GoogleCloudBaseHook, BigQueryHook]
