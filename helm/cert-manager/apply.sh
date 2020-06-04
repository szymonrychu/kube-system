#!/bin/bash

helm repo add jetstack https://charts.jetstack.io

helm upgrade --install --namespace kube-system -f values.yaml cert-manager jetstack/cert-manager


sleep 30

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
#         - '*.szymonrichert.pl'
