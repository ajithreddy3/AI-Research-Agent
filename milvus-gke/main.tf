###############################################################################
# main.tf — Deploy Milvus Helm chart into an existing GKE cluster
# Goal: Reuse an existing cluster (e.g., coco-project) and only manage Milvus.
###############################################################################

provider "helm" {
  kubernetes = {
    config_path = pathexpand("~/.kube/config")
  }
}

# -----------------------------------------------------------------------------
# Namespace
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Milvus (Standalone) + Attu (enabled inside Milvus chart)
# Downsized: disable Pulsar stack and reduce CPU/memory requests
# -----------------------------------------------------------------------------

resource "helm_release" "milvus" {
  name             = "milvus"
  namespace        = var.namespace
  create_namespace = true

  repository = "https://zilliztech.github.io/milvus-helm/"
  chart      = "milvus"

  timeout         = 900
  wait            = true
  wait_for_jobs   = true
  atomic          = true
  cleanup_on_fail = true

  values = [
    yamlencode({
      cluster    = { enabled = false }
      standalone = {
        enabled = true
    }

      pulsar   = { enabled = false }
      pulsarv3 = { enabled = false }
      kafka    = { enabled = false }
      rocksmq  = { enabled = true }

      service = { type = "ClusterIP" }

      persistence = {
        enabled      = true
        size         = "20Gi"
        storageClass = "standard"
      }

      etcd = {
        replicaCount = 1
        persistence  = { enabled = true, size = "10Gi", storageClass = "standard" }

      }
        minio = {
            mode = "standalone"
            persistence = { enabled = true, size = "20Gi", storageClass = "standard" }

        }

      attu = {
        enabled = true
        service = { type = "LoadBalancer", port = 3000 }
      }

    })

  ]
}
