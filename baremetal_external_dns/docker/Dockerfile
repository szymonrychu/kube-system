FROM debian:stable

RUN set -xe;\
    apt-get update && apt-get install --yes --no-install-recommends python3-pip python3-setuptools;\
    pip3 install --upgrade pip;\
    pip3 install ovh kubernetes

COPY ovh_updater.py /

ENTRYPOINT [ "python3", "ovh_updater.py" ]
