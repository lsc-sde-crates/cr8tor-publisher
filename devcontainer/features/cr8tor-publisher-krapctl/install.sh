#!/bin/bash

. /etc/krapctl/environment

cp -R ./modules/* "${KRAPCTL_MODULES}"

mkdir -p /usr/lib/cr8tor-publisher-krapctl/etc
mkdir -p /usr/lib/cr8tor-publisher-krapctl/work
chmod 0777 /usr/lib/cr8tor-publisher-krapctl/work

cat <<EOF > /usr/lib/cr8tor-publisher-krapctl/etc/environment
NAMESPACE="${NAMESPACE}"
APPROVAL_SERVICE_IMAGE_DEFINITION="${APPROVALSERVICEIMAGEDEFINITION}"
METADATA_SERVICE_IMAGE_DEFINITION="${METADATASERVICEIMAGEDEFINITION}"
PUBLISH_SERVICE_IMAGE_DEFINITION="${PUBLISHSERVICEIMAGEDEFINITION}"
HELM_CHART="${HELMCHART}"
KUSTOMIZE_PATH="${KUSTOMIZEPATH}"
EOF

exit 0