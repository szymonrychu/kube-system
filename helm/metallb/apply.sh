#!/bin/bash

helm upgrade --install --namespace kube-system metallb -f values.yaml stable/metallb