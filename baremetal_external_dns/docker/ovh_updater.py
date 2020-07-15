#!/usr/bin/env python3

import os
import ovh, requests, logging
import kubernetes.client, kubernetes.config
from kubernetes.client.rest import ApiException

import time

loglevels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARN': logging.WARN,
    'ERROR': logging.ERROR
}
log_level = loglevels[os.environ.get('LOG_LEVEL', 'INFO')]
logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s]: %(message)s')

client = ovh.Client(
    endpoint=os.environ.get('OVH_APPLICATION_ENDPOINT', 'ovh-eu'),
    application_key=os.environ.get('OVH_APPLICATION_KEY'),
    application_secret=os.environ.get('OVH_APPLICATION_SECRET'),
    consumer_key = os.environ.get('OVH_CONSUMER_KEY')
)
ovh_domain = os.environ.get('OVH_DOMAIN')
ovh_TTL = int(os.environ.get('OVH_TTL', '60'))
ovh_api_sleep_time = int(os.environ.get('OVH_API_SLEEP', '1'))
ovh_main_loop_sleep_time = int(os.environ.get('OVH_UPDATER_SLEEP_TIME', '60'))

try:
    logging.debug('Found Kubernetes local kubeconfig')
    kubernetes.config.load_kube_config()
except Exception:
    logging.debug('Found Kubernetes incluster kubeconfig')
    kubernetes.config.load_incluster_config()

api_instance = kubernetes.client.ExtensionsV1beta1Api()

while True:
    my_ip = requests.get('http://ip.42.pl/raw').text
    # scrape kubernetes ingresses
    ingresses = []
    for ingress in api_instance.list_ingress_for_all_namespaces().items:
        logging.info(f"Found ingress {ingress.metadata.namespace}/{ingress.metadata.name}:")
        for rule in ingress.spec.rules:
            if rule.host:
                if str(rule.host).endswith(ovh_domain):
                    subdomain = str(rule.host)[:-len(ovh_domain)-1]
                    logging.info(f"  -   valid: {subdomain}.{ovh_domain}")
                    ingresses.append(subdomain)
                else:
                    logging.info(f"  - invalid: {rule.host}")


    main_A_record_details = None
    ovh_CNAME_entries_list = []
    ovh_NS_entries_list = []
    ovh_other_entries_list = []
    # scrape OVH
    main_url = f"/domain/zone/{ovh_domain}/record"
    for id in client.get(main_url):
        id_url = f"{main_url}/{id}"
        details = client.get(id_url)
        logging.debug(f"Found {details['subDomain']}.{details['zone']} with a type of {details['fieldType']} pointing to {details['target']}")
        if details['fieldType'] == 'A' and details['zone'] == ovh_domain and details['subDomain'] == '':
            main_A_record_details = details
        elif details['fieldType'] == 'CNAME' and details['zone'] == ovh_domain:
            ovh_CNAME_entries_list.append(details)
        elif details['fieldType'] == 'NS' and details['zone'] == ovh_domain:
            ovh_NS_entries_list.append(details)
        elif details['zone'] == ovh_domain:
            ovh_other_entries_list.append(details)
        else:
            logging.info(f"Ignoring {details['subDomain']}.{details['zone']} with a type of {details['fieldType']} pointing to {details['target']}")

    # fill main A record if it's missing
    if not main_A_record_details:
        logging.info(f"Main A record is missing! Creating {ovh_domain} with TTL {ovh_TTL}s pointing to {my_ip}")
        client.post(main_url, fieldType='A', target=my_ip, ttl=ovh_TTL)
        logging.debug(f"Waiting for {ovh_api_sleep_time} for OVH sanity and to avoid their race conditions!")
        time.sleep(ovh_api_sleep_time)
    elif main_A_record_details['target'] != my_ip:
        logging.info(f"Main A record is present, but target is wrong! Updating {ovh_domain} with TTL {ovh_TTL}s pointing to {my_ip}")
        client.put(f"{main_url}/{main_A_record_details['id']}", fieldType='A', target=my_ip, ttl=ovh_TTL)
        logging.debug(f"Waiting for {ovh_api_sleep_time} for OVH sanity and to avoid their race conditions!")
        time.sleep(ovh_api_sleep_time)
    else:
        logging.info(f"Main A record is present and up to date! No need to update {ovh_domain} with TTL {ovh_TTL}s pointing to {my_ip}")
    
    logging.info('Handling existing OVH entries')
    handled_ingresses = []
    for CNAME_entry in ovh_CNAME_entries_list:
        if str(CNAME_entry['subDomain']) in ingresses:
            if CNAME_entry['target'] == ovh_domain + '.':
                logging.info(f"CNAME {CNAME_entry['subDomain']}.{ovh_domain} pointing to {ovh_domain}, no need to update!")
                handled_ingresses.append(CNAME_entry['subDomain'])
            elif CNAME_entry['target'] != ovh_domain + '.':
                logging.info(f"CNAME {CNAME_entry['subDomain']}.{ovh_domain} NOT pointing to {ovh_domain}, but to {CNAME_entry['target']}, updating!")
                client.put(f"{main_url}/{CNAME_entry['id']}", fieldType='CNAME', target=ovh_domain + '.', ttl=ovh_TTL)
                logging.debug(f"Waiting for {ovh_api_sleep_time} for OVH sanity and to avoid their race conditions!")
                time.sleep(ovh_api_sleep_time)
                handled_ingresses.append(CNAME_entry['subDomain'])
        else:
            logging.info(f"CNAME {CNAME_entry['subDomain']}.{ovh_domain} pointing to {ovh_domain} is not on the list of ingresses, deleting!")
            client.delete(f"{main_url}/{CNAME_entry['id']}")
            logging.debug(f"Waiting for {ovh_api_sleep_time} for OVH sanity and to avoid their race conditions!")
            time.sleep(ovh_api_sleep_time)

    logging.info('Handling missing OVH entries!')
    for ingress_subdomain in ingresses:
        if ingress_subdomain not in handled_ingresses:
            logging.info(f"CNAME {ingress_subdomain}.{ovh_domain} is missing, adding it with TTL {ovh_TTL}s and {ovh_domain} target!")
            client.post(main_url, fieldType='CNAME', target=ovh_domain + '.', ttl=ovh_TTL, subDomain=ingress_subdomain)
            logging.debug(f"Waiting for {ovh_api_sleep_time} for OVH sanity and to avoid their race conditions!")
            time.sleep(ovh_api_sleep_time)

    time.sleep(ovh_main_loop_sleep_time)