#!/usr/bin/env python3

import os
import ovh, requests
import kubernetes.client, kubernetes.config
from kubernetes.client.rest import ApiException

import time


client = ovh.Client(
    endpoint=os.environ.get('OVH_APPLICATION_ENDPOINT', 'ovh-eu'),
    application_key=os.environ.get('OVH_APPLICATION_KEY'),
    application_secret=os.environ.get('OVH_APPLICATION_SECRET'),
    consumer_key = os.environ.get('OVH_CONSUMER_KEY')
)
ovh_domain = os.environ.get('OVH_DOMAIN')

# kubernetes.config.load_kube_config()

kubernetes.config.load_incluster_config()
api_instance = kubernetes.client.ExtensionsV1beta1Api()
main_url = f"/domain/zone/{os.environ.get('OVH_DOMAIN')}/record"

while True:
    ovh_ids = client.get(main_url)
    for id in ovh_ids:
        id_url = f"{main_url}/{id}"
        details = client.get(id_url)
        if details['fieldType'] == 'A' and details['zone'] == os.environ.get('OVH_DOMAIN') and details['subDomain'] == '':
            domain_field = {'fieldType': 'A', 'target': requests.get('http://ip.42.pl/raw').text, 'ttl': 60}
            client.put(f"{main_url}/{details['id']}", **domain_field)
            # {'id': 5120958531, 'zone': 'szymonrichert.pl', 'subDomain': '', 'fieldType': 'A', 'target': '213.186.33.5', 'ttl': 0}


    for ingress in api_instance.list_ingress_for_all_namespaces().items:
        for rule in ingress.spec.rules:
            print(rule)
            if rule.host and str(rule.host).endswith(ovh_domain):
                subdomain_to_update = rule.host[:-len(ovh_domain)-1]
                txt_meta = f"1|szymonrichert.pl"
                records_to_update = [
                    # {'fieldType': 'CNAME', 'target': ovh_domain + '.', 'subDomain': subdomain_to_update, 'ttl': 60},
                    {'fieldType': 'A', 'target': requests.get('http://ip.42.pl/raw').text, 'subDomain': subdomain_to_update, 'ttl': 60},
                    {'fieldType': 'TXT', 'target': txt_meta, 'subDomain': subdomain_to_update},
                ]
                def equals(details1, details2):
                    return details1['fieldType'] == details2['fieldType'] and details1['target'] == details2['target'] and details1['subDomain'] == details2['subDomain']
    
                records = []
                for id in ovh_ids:
                    id_url = f"{main_url}/{id}"
                    details = client.get(id_url)
                    if details['subDomain'] == subdomain_to_update:
                        records.append(details)

                for record_to_update in records_to_update:
                    found = False
                    for record in records:
                        if record['fieldType'] == record_to_update['fieldType']:
                            found = True
                            if not equals(record, record_to_update):
                                client.put(f"{main_url}/{record['id']}", **record_to_update)
                    if not found:
                        client.post(main_url, **record_to_update)
    time.sleep(30)



