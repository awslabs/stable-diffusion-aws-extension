@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

set INITIAL_SUPPORT_COMMIT_ROOT=89f9faa6
set INITIAL_SUPPORT_COMMIT_CONTROLNET=7c674f83
set INITIAL_SUPPORT_COMMIT_DREAMBOOTH=926ae204

set REPO_URL_LIST="https://github.com/Mikubill/sd-webui-controlnet.git https://github.com/d8ahazard/sd_dreambooth_extension.git"
set REPO_FOLDER_LIST="sd-webui-controlnet sd_dreambooth_extension"

:show_help
echo Usage: %~nx0 -p/--pre-flight -s/--version-sync
goto :eof

:get_supported_commit_list
set repo_url=%1
set initial_support_commit=%2
set latest_commit=%3
for /f "tokens=*" %%i in ('git rev-list --topo-order %initial_support_commit%^..%latest_commit%') do echo %%i
goto :eof

:get_latest_commit_id
set repo_url=%1
for /f "tokens=1" %%i in ('git ls-remote "%repo_url%" HEAD ^| findstr /b "[0-9a-f]"') do set latest_commit_id=%%i
echo %latest_commit_id%
goto :eof

:pre_flight_check
echo Start pre-flight check for WebUI...
call :get_latest_commit_id "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git"
set LATEST_ROOT_COMMIT=%latest_commit_id%
echo Supported commits for WebUI:
call :get_supported_commit_list "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git" "%INITIAL_SUPPORT_COMMIT_ROOT%" "%LATEST_ROOT_COMMIT%"
set SUPPORTED_ROOT_COMMITS=%supported_commit_list%
for /f "tokens=*" %%i in ('git -C ..\.. rev-parse HEAD') do set CUR_ROOT_COMMIT=%%i
echo Current commit id for WebUI: %CUR_ROOT_COMMIT%

echo Pre-flight checks complete.

goto :eof

:version_sync
echo Start version sync for WebUI, make sure the extension folder is empty...

set extension_folder=%1
if not exist "%extension_folder%" (
    echo The extension folder does not exist: %extension_folder%
    echo Please create it and run the script again.
    goto :eof
)

echo Syncing WebUI...

for %%r in (%REPO_URL_LIST%) do (
    set repo_url=%%r
    call :get_latest_commit_id !repo_url!
    set latest_commit=!latest_commit_id!

    for %%f in (%REPO_FOLDER_LIST%) do (
        set repo_folder=%%f
        if not exist "%extension_folder%\!repo_folder!" (
            echo Cloning !repo_url! into !repo_folder!...
            git clone !repo_url! "%extension_folder%\!repo_folder!"
            cd "%extension_folder%\!repo_folder!"
            git checkout !latest_commit!
            cd %cd%
        ) else (
            echo Updating !repo_folder! to the latest commit...
            cd "%extension_folder%\!repo_folder!"
            git fetch origin
            git checkout !latest_commit!
            cd %cd%
        )
    )
)

echo Version sync complete.

goto :eof

:parse_options
set options=%*
if not "%options%" == "" (
    for %%o in (%options%) do (
        if "%%o" == "-p" (
            call :pre_flight_check
            exit /b
        ) else if "%%o" == "--pre-flight" (
            call :pre_flight_check
            exit /b
        ) else if "%%o" == "-s" (
            call :version_sync "extensions"
            exit /b
        ) else if "%%o" == "--version-sync" (
            call :version_sync "extensions"
            exit /b
        ) else if "%%o" == "-h" (
            call :show_help
            exit /b
        ) else if "%%o" == "--help" (
            call :show_help
            exit /b
        ) else (
            echo Unknown option: %%o
        )
    )
) else (
    call :show_help
)
goto :eof

call :parse_options %*