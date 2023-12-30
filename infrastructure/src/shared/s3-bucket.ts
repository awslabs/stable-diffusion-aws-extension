import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ResourceProvider } from './resource-provider';


export class S3BucketStore {
  public readonly s3Bucket: s3.Bucket;

  constructor(scope: Construct, id: string, resourceProvider: ResourceProvider, s3BucketName: string) {

    //The code that defines your stack goes here
    // const newBucket = new s3.Bucket(scope, `${id}-aigc-newBucket`, {
    //   bucketName: s3BucketName,
    //   blockPublicAccess: BlockPublicAccess.BLOCK_ACLS,
    //   removalPolicy: RemovalPolicy.RETAIN,
    //   cors: [
    //     {
    //       allowedHeaders: ['*'],
    //       allowedMethods: [s3.HttpMethods.PUT, s3.HttpMethods.HEAD, s3.HttpMethods.GET],
    //       allowedOrigins: ['*'],
    //       exposedHeaders: ['ETag'],
    //     },
    //   ],
    // });


    this.s3Bucket = <s3.Bucket>s3.Bucket.fromBucketName(scope, `${id}-aigc-bucket`, s3BucketName);
    this.s3Bucket.node.addDependency(resourceProvider.resources);

  }
}
