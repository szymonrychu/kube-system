#!/bin/bash

helm upgrade --install --namespace kube-system ingress -f values.yaml stable/nginx-ingress