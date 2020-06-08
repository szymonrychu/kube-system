#!/bin/bash
kubectl get namespace monitoring > /dev/null 2>&1 || kubectl create namespace monitoring
kubectl get namespace emby > /dev/null 2>&1 || kubectl create namespace emby
kubectl get namespace rtorrent > /dev/null 2>&1 || kubectl create namespace rtorrent
kubectl get namespace loki > /dev/null 2>&1 || kubectl create namespace loki
kubectl get namespace octoprint > /dev/null 2>&1 || kubectl create namespace octoprint

kubectl apply -f https://raw.githubusercontent.com/coreos/prometheus-operator/release-0.38/example/prometheus-operator-crd/monitoring.coreos.com_alertmanagers.yaml
kubectl apply -f https://raw.githubusercontent.com/coreos/prometheus-operator/release-0.38/example/prometheus-operator-crd/monitoring.coreos.com_podmonitors.yaml
kubectl apply -f https://raw.githubusercontent.com/coreos/prometheus-operator/release-0.38/example/prometheus-operator-crd/monitoring.coreos.com_prometheuses.yaml
kubectl apply -f https://raw.githubusercontent.com/coreos/prometheus-operator/release-0.38/example/prometheus-operator-crd/monitoring.coreos.com_prometheusrules.yaml
kubectl apply -f https://raw.githubusercontent.com/coreos/prometheus-operator/release-0.38/example/prometheus-operator-crd/monitoring.coreos.com_servicemonitors.yaml
kubectl apply -f https://raw.githubusercontent.com/coreos/prometheus-operator/release-0.38/example/prometheus-operator-crd/monitoring.coreos.com_thanosrulers.yaml


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
    path: "/mnt/disk/prometheus"
EOF

kubectl apply -f - <<EOF
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: emby-local-pv
  labels:
    type: local
spec:
  storageClassName: emby-local-pv
  capacity:
    storage: 500Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/mnt/disk/emby"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: emby-local-pvc
  namespace: emby
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 500Gi
  storageClassName: emby-local-pv
EOF

kubectl apply -f - <<EOF
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: rtorrent-local-pv
  labels:
    type: local
spec:
  storageClassName: rtorrent-local-pv
  capacity:
    storage: 500Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/mnt/disk/emby/medias"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rtorrent-local-pvc
  namespace: rtorrent
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 500Gi
  storageClassName: rtorrent-local-pv
EOF

kubectl apply -f - <<EOF
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: rtorrent-config-local-pv
  labels:
    type: local
spec:
  storageClassName: rtorrent-config-local-pv
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/mnt/disk/rtorrent"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rtorrent-config-local-pvc
  namespace: rtorrent
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: rtorrent-config-local-pv
---
apiVersion: v1
data:
  auth: c3p5bW9ucmk6JDJ5JDEwJE1VMWJBNjRialloNVB1VE1NQ2VIUE92UXo2a0RnVUtsL3NXQmJJendoakZOZEp3VTFzUHZDCg==
kind: Secret
metadata:
  name: rtorrent-external
  namespace: rtorrent
type: Opaque
EOF


helmfile apply

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


kubectl apply -f - <<EOF
---
apiVersion: v1
kind: Service
metadata:
  name: octoprint-external
  namespace: octoprint
spec:
  type: ExternalName
  externalName: 192.168.1.30
---
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    kubernetes.io/ingress.class: nginx
    kubernetes.io/tls-acme: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: octoprint-external
    nginx.ingress.kubernetes.io/auth-realm: 'Octoprint Authentication'
  name: octoprint-external
  namespace: octoprint
spec:
  rules:
  - host: octoprint.szymonrichert.pl
    http:
      paths:
      - backend:
          serviceName: octoprint-external
          servicePort: 5000
        path: /
  tls:
  - hosts:
    - octoprint.szymonrichert.pl
    secretName: octoprint-tls
---
apiVersion: v1
data:
  auth: c3p5bW9ucmk6JDJ5JDEwJE1VMWJBNjRialloNVB1VE1NQ2VIUE92UXo2a0RnVUtsL3NXQmJJendoakZOZEp3VTFzUHZDCg==
kind: Secret
metadata:
  name: octoprint-external
  namespace: octoprint
type: Opaque
EOF

