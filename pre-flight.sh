#!/bin/bash

# Usage: ./pre-flight_check.sh -p to do the pre-flight check for WebUI -s to auto sync the repo and plugin to compatible commit id

INITIAL_SUPPORT_COMMIT_ROOT="89f9faa6"
INITIAL_SUPPORT_COMMIT_CONTROLNET="7c674f83"
INITIAL_SUPPORT_COMMIT_DREAMBOOTH="926ae204"

# built the initial support commit list from option or default value if not provided
INITIAL_SUPPORT_COMMIT_LIST=(
    "${initial_support_commit_controlnet:-7c674f83}"
    "${initial_support_commit_dreambooth:-926ae204}"
)

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
    echo "Usage: $(basename "$0") -p/--pre-flight -s/--version-sync"
}

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

pre_flight_check() {
    echo -e "Start pre-flight check for WebUI..."
    # check if root folder suppport
    LATEST_ROOT_COMMIT=$(get_latest_commit_id "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git")
    # echo -e "Latest commit id for WebUI: \n$LATEST_ROOT_COMMIT"
    SUPPORTED_ROOT_COMMITS=$(cd ../../ && get_supported_commit_list "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git" "$INITIAL_SUPPORT_COMMIT_ROOT" "$LATEST_ROOT_COMMIT")
    # echo -e "Supported commit ids for WebUI: \n$SUPPORTED_ROOT_COMMITS"

    # get current commit id for repo
    CUR_ROOT_COMMIT=$(cd ../../ && git rev-parse HEAD)
    echo -e "Current commit id for WebUI: $CUR_ROOT_COMMIT"
    if [ -n "$LATEST_ROOT_COMMIT" ]; then
        if ! echo "$SUPPORTED_ROOT_COMMITS" | grep -q "$CUR_ROOT_COMMIT"; then
            # warn with red color
            echo "Warning: WebUI's latest commit is not in the minimum supported commit list."
            echo -e "\033[31mPreflight check for WebUI is failed.\033[0m"
            echo -e "==========================================================================="
            echo
        else
            echo "WebUI's latest commit is in the minimum supported commit list."
            echo -e "\033[34mPreflight check for WebUI is successful.\033[0m"
            echo -e "==========================================================================="
            echo
        fi
    fi

    # Get the parent directory of the script
    SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
    PARENT_DIR=$(dirname "$SCRIPT_DIR")

    # Set the repo paths based on the parent directory
    for repo_folder in "${REPO_FOLDER_LIST[@]}"; do
        # set index to increment
        index=$((index+1))
        # check if the repo folder exists
        if [ -d "${PARENT_DIR}/${repo_folder}/.git" ]; then
            echo -e "Repo ${repo_folder} exists in the parent directory of the script."
            # cd to the repo folder
            cd "${PARENT_DIR}/${repo_folder}"
            # get the current commit id for the repo
            LATEST_COMMIT=$(get_latest_commit_id "${REPO_URL_LIST[$index-1]}")
            # echo -e "Latest commit id for Repo ${repo_folder}: \n$LATEST_COMMIT"
            # use such index to set the repo url
            SUPPORTED_COMMITS=$(get_supported_commit_list "${REPO_URL_LIST[$index-1]}" "${INITIAL_SUPPORT_COMMIT_LIST[$index-1]}" "$LATEST_COMMIT")
            # echo -e "Supported commit ids for Repo ${repo_folder} are \n$SUPPORTED_COMMITS"
            CUR_COMMIT=$(git rev-parse HEAD)
            # check if the latest commit id is in the scope of the supported commit list, warn the user if not, and hint success if yes
            if [ -n "$LATEST_COMMIT" ]; then
                if ! echo "$SUPPORTED_COMMITS" | grep -q "$CUR_COMMIT"; then
                    # warn with red color
                    echo "Warning: Repo ${repo_folder}'s latest commit is not in the minimum supported commit list."
                    echo -e "\033[31mPreflight check for Repo ${repo_folder} is failed.\033[0m"
                    echo -e "==========================================================================="
                    echo
                else
                    echo "Repo ${repo_folder}'s latest commit is in the minimum supported commit list."
                    echo -e "\033[34mPreflight check for Repo ${repo_folder} is successful.\033[0m"
                    echo -e "==========================================================================="
                    echo
                fi
            fi
            # back to the parent directory
            cd "$PARENT_DIR"
        fi
    done
}

version_sync() {
    echo -e "Start version sync for WebUI, make sure the extension folder is empty..."

    # check if the extension folder is empty otherwise return directly
    if [ "$(ls -A ../../extensions)" ]; then
        echo "The extension folder is not empty, please make sure it is empty before running this script."
        return
    fi

    cd ../../
    # Reset to specific commit
    git reset --hard ${INITIAL_SUPPORT_COMMIT_ROOT}

    # Go to "extensions" directory
    cd extensions

    # Clone stable-diffusion-aws-extension
    git clone https://github.com/awslabs/stable-diffusion-aws-extension.git

    # Checkout aigc branch
    cd stable-diffusion-aws-extension
    cd ..

    # Clone sd-webui-controlnet
    git clone https://github.com/Mikubill/sd-webui-controlnet.git

    # Go to sd-webui-controlnet directory and reset to specific commit
    cd sd-webui-controlnet
    git reset --hard ${INITIAL_SUPPORT_COMMIT_CONTROLNET}
    cd ..

    # Clone sd_dreambooth_extension
    git clone https://github.com/d8ahazard/sd_dreambooth_extension.git

    # Go to sd_dreambooth_extension directory and reset to specific commit
    cd sd_dreambooth_extension
    git reset --hard ${INITIAL_SUPPORT_COMMIT_DREAMBOOTH}
    cd ..
}

# Parse options with help of getopt
TEMP=$(getopt -o x:y:h:ps -l initial_support_commit_controlnet:,initial_support_commit_dreambooth:,help,pre-flight,version-sync -n "$(basename "$0")" -- "$@")
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
        -p|--pre-flight)
            pre_flight_check
            exit
            ;;
        -s|--version-sync)
            version_sync
            exit
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