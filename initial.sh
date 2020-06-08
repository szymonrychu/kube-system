#!/bin/bash


sudo apt-get update && \
sudo apt-get upgrade -y && \
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common vim git && \
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - && \
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable" && \
sudo apt-get install -y docker-ce && \
sudo systemctl enable docker && \
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add - && \
echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee -a /etc/apt/sources.list.d/kubernetes.list && \
sudo apt-get update && \
sudo apt-get install -y kubelet kubeadm kubernetes-cni && \
sudo kubeadm init --apiserver-cert-extra-sans szymonrichert.pl,szymonrichert.live --pod-network-cidr 10.1.0.0/16 && \
sudo systemctl enable kubelet && \
sudo reboot





kubectl taint nodes --all node-role.kubernetes.io/master-
# kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

sudo mkdir -p /mnt/disk/prometheus
sudo mkdir -p /mnt/disk/emby
sudo chmod 777 /mnt/disk/*
sudo chmod 777 /mnt/disk

./apply.sh