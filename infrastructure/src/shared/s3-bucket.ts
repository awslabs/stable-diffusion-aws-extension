import { aws_s3, CfnCondition, Fn, RemovalPolicy } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { BlockPublicAccess } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';


export class S3BucketStore {
  public readonly s3Bucket: aws_s3.Bucket;

  constructor(scope: Construct, id: string, useExist: string, s3BucketName: string) {
    const shouldCreateBucketCondition = new CfnCondition(
      scope,
      `${id}-shouldCreateBucket`,
      {
        expression: Fn.conditionEquals(useExist, 'no'),
      },
    );

    //The code that defines your stack goes here
    const newBucket = new s3.Bucket(scope, `${id}-aigc-newBucket`, {
      bucketName: s3BucketName,
      blockPublicAccess: BlockPublicAccess.BLOCK_ACLS,
      removalPolicy: RemovalPolicy.RETAIN,
      cors: [
        {
          allowedHeaders: ['*'],
          allowedMethods: [s3.HttpMethods.PUT, s3.HttpMethods.HEAD, s3.HttpMethods.GET],
          allowedOrigins: ['*'],
          exposedHeaders: ['ETag'],
        },
      ],
    });

    (newBucket.node.defaultChild as s3.CfnBucket).cfnOptions.condition = shouldCreateBucketCondition;

    this.s3Bucket = <aws_s3.Bucket>s3.Bucket.fromBucketName(scope, `${id}-aigc-bucket`, s3BucketName);
  }
}
