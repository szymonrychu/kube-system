 #!/bin/bash

CURRENT_PWD=$(pwd)

cd values/$1

if [ -d ./raw ]; then
    cd ./raw
    find . -name "*.pre.yaml" -exec kubectl apply -f {} \;
fi

if [ -d ./scripts ]; then
    cd ./scripts
    find . -name "*.post.sh" -exec bash -e {} \;
fi
