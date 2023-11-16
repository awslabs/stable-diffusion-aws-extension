#!/bin/bash

region=$1
account=$(aws sts get-caller-identity --query Account --output text)

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

  if [[ "$command_exit_code" -eq 0 ]]; then
    ddb_delete_command_output=$(aws dynamodb delete-table --table-name "$i" --output text 2>&1)
    ddb_delete_command_exit_code=$?
    if [[ "$ddb_delete_command_exit_code" -eq 0 ]]; then
      print_info "Table ${i} deleted..."
    fi
  fi
done

print_ok "all dynamodb tables deleted"


print_info "================== Validate KMS ======================"
aliases="$(aws kms list-aliases --query 'Aliases[].AliasName' --output text )"
required_alias=alias/sd-extension-password-key
print_info "checking kms by alias: ${required_alias}"

if [[ "$aliases" == *"$required_alias"* ]]; then
    ddb_alias_command_output=$(aws kms delete-alias --alias-name  "$required_alias" --output text 2>&1)
    ddb_alias_command_exit_code=$?
    if [[ "$ddb_alias_command_exit_code" -eq 0 ]]; then
      print_ok "key alias ${required_alias} is deleted"
    fi
fi


print_info "================== Validate IAM Role ======================"
exist_role=$(aws iam get-role --role-name LambdaStartDeployRole --query 'Role.Arn' --output text)
exist_role_exit_code=$?
if [[ "$exist_role_exit_code" -eq 0 ]]; then
    delete_role_command_output=$(aws iam delete-role --role-name  "LambdaStartDeployRole" --output text 2>&1)
    delete_role_command_exit_code=$?
    if [[ "$delete_role_command_exit_code" -eq 0 ]]; then
      print_info "iam role ${exist_role} is deleted"
    fi

fi
print_ok "IAM Role checked"

print_info "================== Validate SNS Topics ======================"
sns_topics="$(aws sns list-topics --query 'Topics[]' --output text)"
while IFS='' read -r value; do
  print_info "checking topic arn:aws:sns:${region}:${account}:${value} existence"
  if [[ "$sns_topics" == *"$value"* ]]; then
#      aws sns delete-topic --topic-arn "${value}"
    delete_topic_command_output=$(aws sns delete-topic --topic-arn "arn:aws:sns:${region}:${account}:${value}" --output text 2>&1)
    delete_topic_command_exit_code=$?
    if [[ "$delete_topic_command_exit_code" -eq 0 ]]; then
      print_info "found topic arn:aws:sns:${region}:${account}:${value},deleted"
    fi
  fi
done <<<"$(cat retained_sns)"

print_ok "SNS topics checked"

print_info "============================================="
print_ok "[Complete] All resources checked, ok to upgrade"