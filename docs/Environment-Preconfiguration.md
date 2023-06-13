#### **Option 1 (Recommended)**: Use one click AWS Cloudformation Template to install the EC2 instance with WebUI and extension

1. Install the EC2 by using [CloudFormation Template](https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/workshop/ec2.yaml) to install CloudFormation template directly
2. Select the EC2 instance key pair, and keep click with default operation to create the stack
3. Find the output value of the CloudFormation stack, and navigate to the WebUI by clicking the link in the WebUIURL value, note you need to wait extra 5 minutes to wait for the internal setup complete after the stack been created successfully.

#### **Option 2**: Use script if you already had a EC2 instance (Ubuntu 20.04 LTS recommended) without WebUI installed
1. In the working directory of a Linux computer prepared in advance, run the following command to download the latest installation script:
```bash
wget https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/install.sh
```
2. Run the installation script, this script will try to git clone following repos and put the extensions on stable-diffusion-webui extension directory:
   * stable-diffusion-webui
   * stable-diffusion-aws-extension
   * sd-webui-controlnet
   * sd_dreambooth_extension
```bash
sh install.sh
```
>**Notice** :The version of the downloaded repos has been set in the install.sh script, please do not manually change the version, we have tested on the version set in the script.
3. Move to the stable-diffusion-webui folder downloaded by install.sh:
```bash
cd stable-diffusion-webui
```
4. For machines without a GPU, you can start the web UI using the following command:
```bash
./webui.sh --skip-torch-cuda-test
```
5. For machines with a GPU, you can start the web UI using the following command:
```bash
./webui.sh
```