#!/bin/bash

# Define the keyword array to find
FIND_TEXT=("INITIAL_SUPPORT_COMMIT_ROOT=" "INITIAL_SUPPORT_COMMIT_CONTROLNET=" "INITIAL_SUPPORT_COMMIT_DREAMBOOTH=" "INITIAL_SUPPORT_COMMIT_REMBG=" "INITIAL_SUPPORT_COMMIT_SAM=")

# Define the text to replace from input
REPLACE_TEXT=("INITIAL_SUPPORT_COMMIT_ROOT=$1" "INITIAL_SUPPORT_COMMIT_CONTROLNET=$2" "INITIAL_SUPPORT_COMMIT_DREAMBOOTH=$3" "INITIAL_SUPPORT_COMMIT_REMBG=$4" "INITIAL_SUPPORT_COMMIT_SAM=$5")

# Array of files
FILES=("install.sh" "install.bat")

# helper function to hint the script usage
function usage {
    echo "Usage: $0 <initial_support_commit_root> <initial_support_commit_controlnet> <initial_support_commit_dreambooth> <initial_support_commit_rembg> <initial_support_commit_sam>"
    echo "Example: $0 1234567890 1234567890 1234567890 1234567890 1234567890"
    exit 1
}

# Check if the correct number of arguments are passed
if [ "$#" -ne 5 ]; then
    echo "Error: Invalid number of arguments"
    usage
fi

# Loop over the files and replace the text
for FILE in "${FILES[@]}"
do
  if [ -f "$FILE" ]; then
    # loop the FIND_TEXT array and replace the text with corresponding REPLACE_TEXT array
    for i in "${!FIND_TEXT[@]}"; do
        # find the line contain FIND_TEXT and replace the whole line with REPLACE_TEXT
        sed -i "s/${FIND_TEXT[$i]}.*/${REPLACE_TEXT[$i]}/g" $FILE
        echo "Done"
    done
  else
    echo "File $FILE does not exist."
  fi
done
