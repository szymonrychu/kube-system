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

while True:
    ovh_entries = []
    ovh_txt_entries = {}
    ingresses = []
    my_ip = requests.get('http://ip.42.pl/raw').text
    # scrape kubernetes ingresses
    for ingress in api_instance.list_ingress_for_all_namespaces().items:
        print(f"Found ingress {ingress.metadata.namespace}/{ingress.metadata.name}\n  rules:")
        for rule in ingress.spec.rules:
            if rule.host:
                if str(rule.host).endswith(ovh_domain):
                    print(f"  -   valid: {rule.host}")
                    subdomain = str(rule.host)[:-len(ovh_domain)-1]
                    ingresses.append({'name': str(ingress.metadata.name), 'namespace': str(ingress.metadata.namespace), 'host': str(rule.host), 'subDomain': subdomain})
                else:
                    print(f"  - invalid: {rule.host}")

    # scrape OVH
    main_url = f"/domain/zone/{ovh_domain}/record"
    print('OVH entries:')
    for id in client.get(main_url):
        id_url = f"{main_url}/{id}"
        details = client.get(id_url)
        if details['fieldType'] == 'TXT' and details['zone'] == ovh_domain:
            ovh_txt_entries[details['subDomain'] if details['subDomain'] != '' else '~'] = { 'target': details['target'], 'id': details['id'] }
        if details['fieldType'] == 'A' and details['zone'] == ovh_domain:
            print(f"  - subDomain:{details['subDomain']} type:{details['fieldType']} target:{details['target']}")
            if details['subDomain'] != '':
                host = f"{details['subDomain']}.{details['zone']}"
            else:
                host = details['zone']
            ovh_entries.append({'host': host, 'target': details['target'], 'id': details['id'], 'subDomain': details['subDomain'] if details['subDomain'] != '' else '~'})


    # add missing dns entries
    for ingress in ingresses:
        found_entry = False
        for ovh_entry in ovh_entries:
            if ovh_entry['host'] == ingress['host']:
                found_entry = True
                if ovh_entry['subDomain'] in ovh_txt_entries.keys() and ovh_txt_entries[ovh_entry['subDomain']]['target'] == f"1|{ovh_domain}":
                    if ovh_entry['target'] != my_ip:
                        print(f"Updating existing OVH entry {ovh_entry['subDomain']} with ID {ovh_entry['id']}")
                        client.put(f"{main_url}/{ovh_entry['id']}", fieldType='A', target=my_ip, ttl=60)
                    else:
                        print(f"OVH entry {ovh_entry['host']} with ID {ovh_entry['id']} up to date")
                else:
                    print(f"Ignoring existing OVH entry {ovh_entry['host']} with ID {ovh_entry['id']} due lack of TXT entry")
                break
        if not found_entry:
            print(f"Creating missing OVH entry {ingress['host']}")
            client.post(main_url, fieldType='A', target=my_ip, ttl=60, subDomain=ingress['subDomain'])
            client.post(main_url, fieldType='TXT', target=f"1|{ovh_domain}", subDomain=ingress['subDomain'])

    # # delete unnecessary OVH entries not created by us
    for ovh_entry in ovh_entries:
        found_entry = False
        for ingress in ingresses:
            if ovh_entry['host'] == ingress['host']:
                found_entry = True
                break
            
        if not found_entry:
            if ovh_entry['subDomain'] in ovh_txt_entries.keys() and ovh_txt_entries[ovh_entry['subDomain']]['target'] == f"1|{ovh_domain}":
                print(f"Deleting redundant OVH entry {ovh_entry['host']} with ID {ovh_entry['id']}")
                client.delete(f"{main_url}/{ovh_entry['id']}")
            else:
                print(f"Ignoring existing OVH entry {ovh_entry['host']} with ID {ovh_entry['id']} due lack of TXT entry")
    
    time.sleep(int(os.environ.get('OVH_UPDATER_SLEEP_TIME', '60')))