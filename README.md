# RAG_DWYEROMEGA

# export grafana
export POD_NAME=$(kubectl --namespace monitoring get pod -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=prom-stack" -oname)
kubectl --namespace monitoring port-forward $POD_NAME 3000



9hFxiSYa51okx46F4RhnCLvL4sKioW63NPm25rU9


gcloud compute accelerator-types list \
  --filter="zone:( us-central1-a us-central1-b us-central1-c us-central1-f )" \
  --format="table(zone, name, maximumCardsPerInstance)"

ZONE           NAME                   MAXIMUM_CARDS_PER_INSTANCE
us-central1-a  ct3                    4
us-central1-a  ct3p                   4
us-central1-a  ct5l                   8
us-central1-a  ct5lp                  8
us-central1-a  ct5p                   4
us-central1-a  nvidia-a100-80gb       8
us-central1-a  nvidia-h100-80gb       8
us-central1-a  nvidia-h100-mega-80gb  8
us-central1-a  nvidia-l4              8
us-central1-a  nvidia-l4-vws          8
us-central1-a  nvidia-tesla-a100      16
us-central1-a  nvidia-tesla-p4        4
us-central1-a  nvidia-tesla-p4-vws    4
us-central1-a  nvidia-tesla-t4        4
us-central1-a  nvidia-tesla-t4-vws    4
us-central1-a  nvidia-tesla-v100      8
us-central1-b  ct3                    4
us-central1-b  ct3p                   4
us-central1-b  ct6e                   8
us-central1-b  nvidia-b200            8
us-central1-b  nvidia-h100-80gb       8
us-central1-b  nvidia-h100-mega-80gb  8
us-central1-b  nvidia-h200-141gb      8
us-central1-b  nvidia-l4              8
us-central1-b  nvidia-l4-vws          8
us-central1-b  nvidia-tesla-a100      16
us-central1-b  nvidia-tesla-t4        4
us-central1-b  nvidia-tesla-t4-vws    4
us-central1-b  nvidia-tesla-v100      8
us-central1-c  ct6e                   8
us-central1-c  nvidia-a100-80gb       8
us-central1-c  nvidia-h100-80gb       8
us-central1-c  nvidia-h100-mega-80gb  8
us-central1-c  nvidia-l4              8
us-central1-c  nvidia-l4-vws          8
us-central1-c  nvidia-tesla-a100      16
us-central1-c  nvidia-tesla-p100      4
us-central1-c  nvidia-tesla-p100-vws  4
us-central1-c  nvidia-tesla-p4        4
us-central1-c  nvidia-tesla-p4-vws    4
us-central1-c  nvidia-tesla-t4        4
us-central1-c  nvidia-tesla-t4-vws    4
us-central1-c  nvidia-tesla-v100      8
us-central1-f  ct3                    4
us-central1-f  ct3p                   4
us-central1-f  nvidia-tesla-a100      16
us-central1-f  nvidia-tesla-p100      4
us-central1-f  nvidia-tesla-p100-vws  4
us-central1-f  nvidia-tesla-t4        4
us-central1-f  nvidia-tesla-t4-vws    4
us-central1-f  nvidia-tesla-v100      8


gcloud compute regions describe us-central1 \
  --flatten="quotas[]" \
  --format="table(quotas.metric,quotas.limit,quotas.usage)" \
  | grep NVIDIA

NVIDIA_K80_GPUS                                      1.0          0.0
NVIDIA_P100_GPUS                                     1.0          0.0
PREEMPTIBLE_NVIDIA_K80_GPUS                          1.0          0.0
PREEMPTIBLE_NVIDIA_P100_GPUS                         1.0          0.0
NVIDIA_P100_VWS_GPUS                                 1.0          0.0
NVIDIA_V100_GPUS                                     1.0          0.0
NVIDIA_P4_GPUS                                       1.0          0.0
NVIDIA_P4_VWS_GPUS                                   1.0          0.0
PREEMPTIBLE_NVIDIA_V100_GPUS                         1.0          0.0
PREEMPTIBLE_NVIDIA_P4_GPUS                           1.0          0.0
PREEMPTIBLE_NVIDIA_P100_VWS_GPUS                     1.0          0.0
PREEMPTIBLE_NVIDIA_P4_VWS_GPUS                       1.0          0.0
NVIDIA_T4_GPUS                                       0.0          0.0
NVIDIA_T4_VWS_GPUS                                   0.0          0.0
PREEMPTIBLE_NVIDIA_T4_GPUS                           0.0          0.0
PREEMPTIBLE_NVIDIA_T4_VWS_GPUS                       0.0          0.0
COMMITTED_NVIDIA_K80_GPUS                            0.0          0.0
COMMITTED_NVIDIA_P100_GPUS                           0.0          0.0
COMMITTED_NVIDIA_P4_GPUS                             0.0          0.0
COMMITTED_NVIDIA_V100_GPUS                           0.0          0.0
COMMITTED_NVIDIA_T4_GPUS                             0.0          0.0
NVIDIA_A100_GPUS                                     0.0          0.0
PREEMPTIBLE_NVIDIA_A100_GPUS                         0.0          0.0
COMMITTED_NVIDIA_A100_GPUS                           0.0          0.0
NVIDIA_A100_80GB_GPUS                                0.0          0.0
PREEMPTIBLE_NVIDIA_A100_80GB_GPUS                    0.0          0.0
COMMITTED_NVIDIA_A100_80GB_GPUS                      0.0          0.0
NVIDIA_L4_GPUS                                       0.0          0.0
PREEMPTIBLE_NVIDIA_L4_GPUS                           0.0          0.0
COMMITTED_NVIDIA_L4_GPUS                             0.0          0.0


Latest grafana pass: SZf8FPC1kZdfBvkqqEd7JZga0Yt8QCdFKjLaRlTy