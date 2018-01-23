variable "project" {
  default = "blog-180218"
}

variable "postgres_user" {
  default = "airflow"
}
variable "postgres_pw" {
  default = "airflow"
}

variable "region" {
  default = "us-central1"
}

variable "zone" {
  default = "us-central1-f"
}

provider "google" {
  version = "~> 1.4"
  project = "${var.project}"
  region = "${var.region}"
}

resource "google_compute_disk" "airflow-redis-disk" {
  name  = "airflow-redis-disk"
  type  = "pd-ssd"
  size = "200"
  zone  = "${var.zone}"
}

resource "google_sql_database_instance" "airflow-db" {
  name = "airflow-db-test1"
  database_version = "POSTGRES_9_6"
  region = "${var.region}"
  settings {
    tier = "db-f1-micro"
  }
}

resource "google_sql_database" "airflow-schema" {
  name = "airflow"
  instance = "${google_sql_database_instance.airflow-db.name}"
}

resource "google_sql_user" "proxyuser" {
  name = "${var.postgres_user}"
  password = "${var.postgres_pw}"
  instance = "${google_sql_database_instance.airflow-db.name}"
  host = "cloudsqlproxy~%"
}

resource "google_container_cluster" "airflow-cluster" {
  name = "airflow-cluster"
  zone = "${var.zone}"
  initial_node_count = "2"
  node_config {
    machine_type = "n1-standard-4"
  }
}
