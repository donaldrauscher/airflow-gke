# Deploying Airflow on Google Kubernetes Engine

## About

I leveraged [an awesome Docker image with Airflow](https://github.com/puckel/docker-airflow).  Terraform for managing GCP infrastructure.  Postgres instance on CloudSQL for the Airflow meta database. Used [`ktmpl`](https://github.com/jimmycuadra/ktmpl) for performing parameter substitutions in Kubernetes manifest.  Also used [git-sync](https://github.com/kubernetes/git-sync) sidecar container to continuously sync DAGs and plugins on running cluster, so only need to rebuild Docker image when changing Python environment.

Note: To run Citibike example pipeline, will need to create a Service Account with BigQuery access and add to the `google_cloud_default` [Connection](https://airflow.apache.org/concepts.html#connections) in Airflow UI.

## Deploy Instructions

### (1) Store project id, git repo, and Fernet key as env variables
```
export PROJECT_ID=$(gcloud config get-value project -q)
export DAG_REPO=$(git remote get-url --all origin)

if [ ! -f './fernet.key' ]; then
  export FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; FERNET_KEY = Fernet.generate_key().decode(); print(FERNET_KEY)")
  echo $FERNET_KEY > fernet.key
else
  export FERNET_KEY=$(cat fernet.key)
fi
```

### (2) Create Docker image and upload to Google Container Repository
```
docker build -t airflow-gke:latest .
docker tag airflow-gke gcr.io/${PROJECT_ID}/airflow-gke:latest
gcloud docker -- push gcr.io/${PROJECT_ID}/airflow-gke
```

### (3) Create infrastructure with Terraform
```
terraform apply -var $(printf 'project=%s' $PROJECT_ID)
```

### (4) Deploy on Kubernetes

Note: You will also need to create a Service Account for the CloudSQL proxy in Kubernetes.  Create that (Role = "Cloud SQL Client") and download the JSON key.  Stored in `.keys/airflow-cloud.json` in this example.

```
gcloud container clusters get-credentials airflow-cluster
gcloud config set container/cluster airflow-cluster

kubectl create secret generic cloudsql-instance-credentials \
  --from-file=credentials.json=.keys/airflow-cloudsql.json

ktmpl airflow-k8s.yaml \
  --parameter PROJECT_ID ${PROJECT_ID} \
  --parameter FERNET_KEY ${FERNET_KEY} \
  --parameter DAG_REPO ${DAG_REPO} | kubectl apply -f -
```
