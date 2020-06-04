#!/bin/bash

kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: prometheus-local-pvc
  labels:
    type: local
spec:
  storageClassName: prometheus-local-pvc
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/mnt/prometheus-local-pvc"
EOF

kubectl get namespace monitoring > /dev/null 2>&1 || kubectl create namespace monitoring

helmfile apply

kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1alpha2
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
  namespace: kube-system
spec:
  acme:
    email: szymon.rychu@gmail.com
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
      selector:
        dnsZones:
        - 'szymonrichert.pl'

EOF