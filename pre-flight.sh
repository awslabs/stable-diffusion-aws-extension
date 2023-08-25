#!/bin/bash

# Usage: ./pre-flight_check.sh -p to do the pre-flight check for WebUI -s to auto sync the repo and plugin to compatible commit id

INITIAL_SUPPORT_COMMIT_ROOT=68f336bd994bed5442ad95bad6b6ad5564a5409a
INITIAL_SUPPORT_COMMIT_CONTROLNET=efda6ddfd82ebafc6e1150fbb7e1f27163482a82
INITIAL_SUPPORT_COMMIT_DREAMBOOTH=c2a5617c587b812b5a408143ddfb18fc49234edf
INITIAL_SUPPORT_COMMIT_REMBG=3d9eedbbf0d585207f97d5b21e42f32c0042df70
INITIAL_SUPPORT_COMMIT_SAM=5df716be8445e0f358f6e8d4b65a87cc611bfe08
INITIAL_SUPPORT_COMMIT_TILEDVAE=f9f8073e64f4e682838f255215039ba7884553bf

# built the initial support commit list from option or default value if not provided
INITIAL_SUPPORT_COMMIT_LIST=(
    "${initial_support_commit_controlnet:-7c674f83}"
    "${initial_support_commit_dreambooth:-926ae204}"
)

# Fixed repo URLs list
REPO_URL_LIST=(
    "https://github.com/Mikubill/sd-webui-controlnet.git"
    "https://github.com/d8ahazard/sd_dreambooth_extension.git"
    "https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git"
    "https://github.com/continue-revolution/sd-webui-segment-anything.git"
    "https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git"
)

REPO_FOLDER_LIST=(
    "sd-webui-controlnet"
    "sd_dreambooth_extension"
    "stable-diffusion-webui-rembg"
    "sd-webui-segment-anything"
    "multidiffusion-upscaler-for-automatic1111"
)

show_help() {
    echo "Usage: $(basename "$0") [options]
        -h/--help: to show this help;\n
        -p/--pre-flight: to check version compatibility;\n
        -s/--version-sync: to sync the repo and plugin to compatible commit id;\n
        -f/--force: to force skip the folder check when sync the version";
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
    # check if root folder support
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

    # check if the extension folder is empty and force option is not included
    if [ "$(ls -A ../../extensions)" ] && [ "$1" != "-f" ] && [ "$1" != "--force" ]; then
        echo "The extension folder is not empty, continue to sync the version will overwrite the existing files."
        # confirm to proceed
        read -p "Do you want to proceed? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Exiting..."
            exit 1
        fi
    fi

    cd ../../
    # Reset to specific commit
    git checkout master
    git pull
    git reset --hard ${INITIAL_SUPPORT_COMMIT_ROOT}

    # Go to "extensions" directory
    cd extensions

    # Clone stable-diffusion-aws-extension if not exist
    if [ ! -d "stable-diffusion-aws-extension" ]; then
        git clone https://github.com/awslabs/stable-diffusion-aws-extension.git
    fi
    # Checkout aigc branch
    cd stable-diffusion-aws-extension
    cd ..

    # Clone sd-webui-controlnet if not exist
    if [ ! -d "sd-webui-controlnet" ]; then
        git clone https://github.com/Mikubill/sd-webui-controlnet.git
    fi
    # Go to sd-webui-controlnet directory and reset to specific commit
    cd sd-webui-controlnet
    git checkout main
    git pull
    git reset --hard ${INITIAL_SUPPORT_COMMIT_CONTROLNET}
    cd ..

    # Clone sd_dreambooth_extension if not exist
    if [ ! -d "sd_dreambooth_extension" ]; then
        git clone https://github.com/d8ahazard/sd_dreambooth_extension.git
    fi
    # Go to sd_dreambooth_extension directory and reset to specific commit
    cd sd_dreambooth_extension
    git checkout main
    git pull
    git reset --hard ${INITIAL_SUPPORT_COMMIT_DREAMBOOTH}
    cd ..

    # Clone stable-diffusion-webui-rembg
    git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git

    # Go to stable-diffusion-webui-rembg directory and reset to specific commit
    cd stable-diffusion-webui-rembg
    git reset --hard ${INITIAL_SUPPORT_COMMIT_REMBG}
    cd ..

    # Clone sd-webui-segment-anything
    git clone https://github.com/continue-revolution/sd-webui-segment-anything.git

    # Go to sd-webui-segment-anything directory and reset to specific commit
    cd sd-webui-segment-anything
    git reset --hard ${INITIAL_SUPPORT_COMMIT_SAM}
    cd ..

    # Go to multidiffusion-upscaler-for-automatic1111 directory and reset to specific commit
    cd multidiffusion-upscaler-for-automatic1111
    git reset --hard ${INITIAL_SUPPORT_COMMIT_TILEDVAE}
    cd ..
}

# Parse options with help of getopt
TEMP=$(getopt -o x:y:hpsf -l initial_support_commit_controlnet:,initial_support_commit_dreambooth:,help,pre-flight,version-sync,force -n "$(basename "$0")" -- "$@")
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
        -f|--force)
            version_sync -f
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