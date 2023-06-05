#!/bin/bash

# Define the AMI name pattern for Ubuntu Server 20.04 LTS (HVM), SSD Volume Type
AMI_NAME_PATTERN="ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"

# Get the list of all available regions
REGIONS=$(aws ec2 describe-regions --query 'Regions[].RegionName' --output text)

# Initialize an empty output string
output=""

# Loop through each region and find the matching AMI
for region in $REGIONS; do
  ami_id=$(aws ec2 describe-images --filters "Name=name,Values=$AMI_NAME_PATTERN" --region "$region" --query 'Images[0].ImageId' --output text)
  
  if [ "$ami_id" != "None" ]; then
    output+="$region:\n  AMI: $ami_id\n"
  else
    output+="$region:\n  AMI: None\n"
  fi
done

# Print the output in the desired format
echo -e "$output"