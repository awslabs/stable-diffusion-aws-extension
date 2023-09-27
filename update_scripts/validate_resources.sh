#!/bin/bash

RED='\033[0;31m'
Green='\033[0;32m'
Blue='\033[0;34m'
NC='\033[0m' # No Color

function print_error {
  printf "${RED}[Error] %s ${NC}\n" "$1"
}

function print_ok {
  printf "${Green}[Success] %s ${NC}\n" "$1"
}

function print_info {
  printf "${Blue}[Info] %s ${NC}\n" "$1"
}

print_info "================== Validate DynamoDB ======================"
ddb_tables_arr=()
while IFS='' read -r value; do
    ddb_tables_arr+=("$value")
done <<<"$(cat retained_ddb)"

#printf '%s\n' "${ddb_tables_arr[@]}"

for i in "${ddb_tables_arr[@]}"
do
  print_info "checking ${i} table existence"
  command_output=$(aws dynamodb describe-table --table-name "$i" --output text 2>&1)
  command_exit_code=$?

  if [[ "$command_exit_code" -ne 0 ]]; then
    if [[ "${command_output}" =~ "An error occurred (ResourceNotFoundException)" ]]; then
      print_error "Table ${i} not found, please create one"
      exit 1
    fi
  fi
done
print_ok "all dynamodb tables checked"


print_info "================== Validate KMS ======================"
aliases="$(aws kms list-aliases --query 'Aliases[].AliasName' --output text )"
required_alias=alias/sd-extension-password-key
print_info "checking kms by alias: ${required_alias}"

if [[ "$aliases" == *"$required_alias"* ]]; then
    print_ok "key ${required_alias} is ok"
  else
    print_error "key ${required_alias} is not exist, please create one"
    exit 1
fi


print_info "================== Validate IAM Role ======================"
exist_role=$(aws iam get-role --role-name LambdaStartDeployRole --query 'Role.Arn' --output text)
exist_role_exit_code=$?
if [[ "$exist_role_exit_code" -ne 0 ]]; then
    if [[ "${command_output}" =~ "An error occurred (NoSuchEntity)" ]]; then
      print_error "IAM Role LambdaStartDeployRole not found, please create one"
      exit 1
    fi
fi
print_ok "IAM Role checked"

print_info "================== Validate SNS Topics ======================"
sns_topics="$( aws sns list-topics --query 'Topics[]' --output text)"
while IFS='' read -r value; do
  if [[ "$sns_topics" == *"$value"* ]]; then
      print_info "found topic ${value}"
    else
      print_error "not find topic ${value}"
      exit 1
  fi
done <<<"$(cat retained_sns)"

print_ok "SNS topics checked"

print_info "============================================="
print_ok "[Complete] All resources checked, ok to upgrade"


