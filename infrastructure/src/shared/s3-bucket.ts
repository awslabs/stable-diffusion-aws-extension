import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';


export class S3BucketStore {
  public readonly s3Bucket: Bucket;

  constructor(scope: Construct, id: string, s3BucketName: string) {

    this.s3Bucket = <Bucket>Bucket.fromBucketName(scope, `${id}-aigc-bucket`, s3BucketName);

  }
}
