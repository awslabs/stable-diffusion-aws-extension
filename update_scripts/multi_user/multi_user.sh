#!/bin/bash

# create new user table
aws dynamodb create-table --billing-mode PAY_PER_REQUEST --cli-input-json file://user_table.json

# create kms key for password encryption
keyID=$(aws kms create-key | jq -r '.KeyMetadata.KeyId')
echo "kms key id: ${keyID}"
aws kms create-alias --alias-name alias/sd-extension-password-key --target-key-id $keyID

