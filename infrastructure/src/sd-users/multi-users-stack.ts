import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_dynamodb,
  aws_kms,
  CfnCondition,
  Fn,
  NestedStack,
  RemovalPolicy,
  StackProps,
} from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Construct } from 'constructs';
import { RoleUpsertApi } from './role-upsert-api';
import { ListAllRolesApi } from './roles-listall-api';
import { UserDeleteApi } from './user-delete-api';
import { UserUpsertApi } from './user-upsert-api';
import { ListAllUsersApi } from './users-listall-api';


export interface MultiUsersStackProps extends StackProps {
  multiUserTable: aws_dynamodb.Table;
  routers: {[key: string]: Resource};
  commonLayer: PythonLayerVersion;
  useExist: string;
}

export class MultiUsersStack extends NestedStack {
  private readonly srcRoot='../middleware_api/lambda';

  constructor(scope: Construct, id: string, props: MultiUsersStackProps) {
    super(scope, id, props);

    const shouldCreatePasswordKeyCondition = new CfnCondition(
      scope,
      `${id}-shouldCreateUseExistPasswordKey`,
      {
        expression: Fn.conditionEquals(props.useExist, 'no'),
      },
    );
    const keyAlias = 'sd-extension-password-key';
    const newPasswordKey = new aws_kms.Key(scope, `${id}-password-key`, {
    // const passwordKey = new aws_kms.Key(scope, `${id}-password-key`, {
      description: 'a custom key for sd extension to encrypt and decrypt password',
      // alias: keyAlias,
      removalPolicy: RemovalPolicy.RETAIN,
      enableKeyRotation: false,
    });

    const newKeyAlias = new aws_kms.Alias(scope, `${id}-passwordkey-alias`, {
      aliasName: keyAlias,
      removalPolicy: RemovalPolicy.RETAIN,
      targetKey: newPasswordKey,
      // targetKey: passwordKey,
    });

    (newPasswordKey.node.defaultChild as aws_kms.CfnKey).cfnOptions.condition = shouldCreatePasswordKeyCondition;
    (newKeyAlias.node.defaultChild as aws_kms.CfnAlias).cfnOptions.condition = shouldCreatePasswordKeyCondition;
    const passwordKey = aws_kms.Alias.fromAliasName(scope, `${id}-createOrNew-passwordKey`, keyAlias);

    new RoleUpsertApi(scope, 'roleUpsert', {
      commonLayer: props.commonLayer,
      httpMethod: 'POST',
      multiUserTable: props.multiUserTable,
      router: props.routers.role,
      srcRoot: this.srcRoot,
    });

    new ListAllRolesApi(scope, 'roleListAll', {
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      multiUserTable: props.multiUserTable,
      router: props.routers.roles,
      srcRoot: this.srcRoot,
    });

    new UserUpsertApi(scope, 'userUpsert', {
      commonLayer: props.commonLayer,
      httpMethod: 'POST',
      multiUserTable: props.multiUserTable,
      passwordKey: passwordKey,
      router: props.routers.user,
      srcRoot: this.srcRoot,
    });

    new UserDeleteApi(scope, 'userDelete', {
      commonLayer: props.commonLayer,
      httpMethod: 'DELETE',
      multiUserTable: props.multiUserTable,
      router: props.routers.user,
      srcRoot: this.srcRoot,
    });

    new ListAllUsersApi(scope, 'userListAll', {
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      multiUserTable: props.multiUserTable,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      passwordKey: passwordKey,
    });

  }
}
