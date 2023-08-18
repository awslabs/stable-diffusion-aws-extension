# Version Upgrade Workaround

Since the dynamodb names keep the same in the cloudformation, deleting the previous cloudformation stack and creating a new one might be the only way to upgrade.
But if we go this way, all datas in the dynamodb will be lost, including the models we've uploade, inferences we've done etc.

It's a workaround for stable-diffusion-aws-extension version upgrade.

find the details in the [issue](https://github.com/awslabs/stable-diffusion-aws-extension/issues/165)



## Workaround steps

1. Set up your aws environment, ensure you can run AWS CLI and Python with boto3

2. Run `before_run_cf.py`, the script will backup all dynamodb datas

3. Find and save current S3BucketName in the cloudformation outputs

4. Delete current CloudFormation Stack, fix the problem if resources fail to be deleted. **Note that the S3 bucket will not be deleted.**
5. Create and run a new CloudFormation Stack, fix the problem if resources fail to be created
6. Find and save the new S3BucketName in the cloudformation outputs, like step 3
7. Edit `after_run_fc.py` and set `src_bucket` and `dst_bucket` with two S3BucketName saved in step3 and step6
8. Run `after_run_cf.py`, the script will:
   1. Delete all ddb tables created by cloudformation for restoring
   2. Restore all ddb tables
   3. Sync all datas from `src_bucket` to `dst_bucket`. **It might take a long time to sync if your bucket size is large, finding a more efficient solution.**
   4. Check if all tables are restored successfully, delete all backups.
9. Delete Sagemaker Endpoint & Endpoint configuration & Models created by previous middleware, we cannot reuse those resource because the `S3 output path` in the Endpoint configuration is different
10. Deploy New Sagemaker Endpoint on WebUI
11. Wait and test
