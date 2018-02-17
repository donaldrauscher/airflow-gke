# Deploying Airflow on Google Kubernetes Engine

## About

I leveraged [an awesome Docker image with Airflow](https://github.com/puckel/docker-airflow).  Terraform for managing GCP infrastructure.  Postgres instance on CloudSQL for the Airflow meta database. I used [git-sync](https://github.com/kubernetes/git-sync) sidecar container to continuously sync DAGs and plugins on running cluster, so only need to rebuild Docker image when changing Python environment.  Packaged all Kubernetes resources in [a Helm chart](https://helm.sh/).  

Note: Having a self-signed cert is obviously far from ideal.  However, I only set up HTTPS because I secured my instance with [Cloud IAP](https://cloud.google.com/iap/), which requires a HTTPS load balancer.

TODO: Implement something like [this](https://github.com/jetstack/kube-lego) to automatically request certificates from [Let's Encrypt](https://letsencrypt.org/).

Note: To run Citibike example pipeline, will need to create a Service Account with BigQuery access and add to the `google_cloud_default` [Connection](https://airflow.apache.org/concepts.html#connections) in Airflow UI.

## Deploy Instructions

### (1) Store project id and Fernet key as env variables; create SSL cert / key

``` bash
export PROJECT_ID=$(gcloud config get-value project -q)

if [ ! -f '.keys/fernet.key' ]; then
  export FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; FERNET_KEY = Fernet.generate_key().decode(); print(FERNET_KEY)")
  echo $FERNET_KEY > .keys/fernet.key
else
  export FERNET_KEY=$(cat .keys/fernet.key)
fi

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout .keys/tls.key \
  -out .keys/tls.crt \
  -subj "/CN=cloudiap/O=cloudiap"
```

### (2) Create Docker image and upload to Google Container Repository

``` bash
docker build -t airflow-gke:latest .
docker tag airflow-gke gcr.io/${PROJECT_ID}/airflow-gke:latest
gcloud docker -- push gcr.io/${PROJECT_ID}/airflow-gke
```

### (3) Create infrastructure with Terraform

Note: You will also need to create a Service Account for the CloudSQL proxy in Kubernetes.  Create that (Role = "Cloud SQL Client"), download the JSON key, and attach as secret.  Stored in `.keys/airflow-cloudsql.json` in this example.

``` bash
terraform apply -var project=${PROJECT_ID}

gcloud container clusters get-credentials airflow-cluster
gcloud config set container/cluster airflow-cluster

kubectl create secret generic cloudsql-instance-credentials \
  --from-file=credentials.json=.keys/airflow-cloudsql.json

kubectl create secret tls cloudiap \
  --cert=.keys/tls.crt --key=.keys/tls.key

helm init
```

### (4) Deploy with Kubernetes

``` bash
helm install . \
  --set projectId=${PROJECT_ID} \
  --set fernetKey=${FERNET_KEY}
```
