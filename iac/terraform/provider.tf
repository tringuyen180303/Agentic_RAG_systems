provider "google" {
    project = var.project_id
    region = var.region
}

resource "google_container_cluster" "primary" {
  name               = "${var.project_id}-gke"
  location           = var.region
  initial_node_count = 3
}

resource "google_container_node_pool" "default_pool" {
  name               = "${var.project_id}-node-pool"
  cluster            = google_container_cluster.primary.name
  location           = google_container_cluster.primary.location
  initial_node_count = 3

  node_config {
    machine_type = "n1-standard-2"
    disk_size_gb = 100
  }

   autoscaling {
    min_node_count = 1
    max_node_count = 3
  }

}