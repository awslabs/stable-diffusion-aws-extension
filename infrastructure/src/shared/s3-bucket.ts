import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ResourceProvider } from './resource-provider';


export class S3BucketStore {
  public readonly s3Bucket: s3.Bucket;

  constructor(scope: Construct, id: string, resourceProvider: ResourceProvider, s3BucketName: string) {

    this.s3Bucket = <s3.Bucket>s3.Bucket.fromBucketName(scope, `${id}-aigc-bucket`, s3BucketName);
    this.s3Bucket.node.addDependency(resourceProvider.resources);

  }
}
