**Part1**: Install the stable-diffusion-webui and extension

#### **Option 1 (Recommended)**: Use one-click AWS Cloudformation template to install the EC2 instance with WebUI and extension

1. Download the CloudFormation Template from [link](https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/workshop/ec2.yaml)

2. Sign in to the [AWS Management Console](https://console.aws.amazon.com/) and go to [CloudFormation console](https://console.aws.amazon.com/cloudformation/)

3. On the Stacks page, choose **Create stack**, and then choose **With new resources (standard)**.

4. On the **Specify template** page, choose **Template is ready**, choose **Upload a template file**, and then browse for the template that is downloaded in step 1, and then choose **Next**.

5. On the **Specify stack details** page, type a stack name in the Stack name box. Choose an EC2 instance key pair, then choose **Next**.

6. On the **Configure stack options** page, choose **Next**.

7. On the **Review** page, review the details of your stack, and choose **Submit**.

8. Wait until the stack is created.

9. Find the output value of the CloudFormation stack, and navigate to the WebUI by clicking the link in the **WebUIURL** value, note you need to wait extra 5 minutes to wait for the internal setup complete after the stack been created successfully.

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