#!/bin/bash

# Usage: ./preflight_check.sh -x [initial_support_commit_controlnet] -y [initial_support_commit_dreambooth]
# ecc84a28 83d7f75c

# Fixed repo URLs list
REPO_URL_LIST=(
    "https://github.com/Mikubill/sd-webui-controlnet.git"
    "https://github.com/d8ahazard/sd_dreambooth_extension.git"
)

REPO_FOLDER_LIST=(
    "sd-webui-controlnet"
    "sd_dreambooth_extension"
)

show_help() {
    echo "Usage: $(basename "$0") -x/--initial_support_commit_controlnet <commit id> -y/--initial_support_commit_dreambooth <commit id>"
}

# Parse options with help of getopt
TEMP=$(getopt -o x:y:h -l initial_support_commit_controlnet:,initial_support_commit_dreambooth:,help -n "$(basename "$0")" -- "$@")
eval set -- "$TEMP"

while true; do
    case "$1" in
        -x|--initial_support_commit_controlnet)
            initial_support_commit_controlnet="$2"
            shift 2
            ;;
        -y|--initial_support_commit_dreambooth)
            initial_support_commit_dreambooth="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Internal error!"
            exit 1
            ;;
    esac
done

# built the initial support commit list from option or default
INITIAL_SUPPORT_COMMIT_LIST=(
    "$initial_support_commit_controlnet"
    "$initial_support_commit_dreambooth"
)

# Function to get supported commit list
get_supported_commit_list() {
    repo_url="$1"
    initial_support_commit="$2"
    latest_commit="$3"
    # echo "the repo url is $repo_url and the initial support commit is $initial_support_commit and the latest commit is $latest_commit and current folder is $(pwd)"
    # list all the commit ids start from the initial support commit to the latest commit
    commit_ids=$(git rev-list --topo-order $initial_support_commit^..$latest_commit)
    echo "$commit_ids"
}


# Function to get current commit id of existing repo
get_latest_commit_id() {
    repo_url="$1"
    git ls-remote "$repo_url" HEAD | cut -f1
}

# Get the parent directory of the script
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PARENT_DIR=$(dirname "$SCRIPT_DIR")

# Set the repo paths based on the parent directory
for repo_folder in "${REPO_FOLDER_LIST[@]}"; do
    # set index to increment
    index=$((index+1))
    # check if the repo folder exists
    if [ -d "${PARENT_DIR}/${repo_folder}/.git" ]; then
        echo "Repo ${repo_folder} exists in the parent directory of the script."
        # cd to the repo folder
        cd "${PARENT_DIR}/${repo_folder}"
        # get the current commit id for the repo
        LATEST_COMMIT=$(get_latest_commit_id "${REPO_URL_LIST[$index-1]}")
        echo "Latest commit id for Repo ${repo_folder}: $LATEST_COMMIT"
        # use such index to set the repo url
        SUPPORTED_COMMITS=$(get_supported_commit_list "${REPO_URL_LIST[$index-1]}" "${INITIAL_SUPPORT_COMMIT_LIST[$index-1]}" "$LATEST_COMMIT")
        echo "Supported commit ids for Repo ${repo_folder} are $SUPPORTED_COMMITS"
        # check if the latest commit id is in the scope of the supported commit list, warn the user if not, and hint success if yes
        if [ -n "$LATEST_COMMIT" ]; then
            if ! echo "$SUPPORTED_COMMITS" | grep -q "$LATEST_COMMIT"; then
                # warn with red color
                echo "Warning: Repo ${repo_folder}'s latest commit is not in the supported commit list."
                echo -e "\033[31mPreflight check for Repo ${repo_folder} is failed.\033[0m"
                echo -e "==========================================================================="
            else
                echo "Repo ${repo_folder}'s latest commit is in the supported commit list."
                echo -e "\033[34mPreflight check for Repo ${repo_folder} is successful.\033[0m"
                echo -e "==========================================================================="
            fi
        fi
        # back to the parent directory
        cd "$PARENT_DIR"
    fi
done