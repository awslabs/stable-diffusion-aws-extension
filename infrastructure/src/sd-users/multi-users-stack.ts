import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import {aws_apigateway, aws_dynamodb, aws_kms, CfnParameter, NestedStack, StackProps} from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Construct } from 'constructs';
import { CreateRoleApi } from '../api/roles/create-role';
import { DeleteRolesApi, DeleteRolesApiProps } from '../api/roles/delete-roles';
import { ListRolesApi } from '../api/roles/list-roles';
import { CreateUserApi } from '../api/users/create-user';
import { DeleteUsersApi } from '../api/users/delete-users';
import { ListUsersApi } from '../api/users/list-users';
import {ResourceProvider} from "../shared/resource-provider";


export interface MultiUsersStackProps extends StackProps {
  multiUserTable: aws_dynamodb.Table;
  routers: { [key: string]: Resource };
  commonLayer: PythonLayerVersion;
  resourceProvider: ResourceProvider;
  passwordKeyAlias: aws_kms.IKey;
  authorizer: aws_apigateway.IAuthorizer;
  logLevel: CfnParameter;
}

export class MultiUsersStack extends NestedStack {
  private readonly srcRoot = '../middleware_api/lambda';

  constructor(scope: Construct, id: string, props: MultiUsersStackProps) {
    super(scope, id, props);

    // POST /roles
    new CreateRoleApi(scope, 'CreateRole', {
      commonLayer: props.commonLayer,
      httpMethod: 'POST',
      multiUserTable: props.multiUserTable,
      router: props.routers.roles,
      srcRoot: this.srcRoot,
      logLevel: props.logLevel,
    });

    // GET /roles
    new ListRolesApi(scope, 'ListRoles', {
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      multiUserTable: props.multiUserTable,
      router: props.routers.roles,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
      logLevel: props.logLevel,
    });

    // POST /users
    new CreateUserApi(scope, 'CreateUser', {
      commonLayer: props.commonLayer,
      httpMethod: 'POST',
      multiUserTable: props.multiUserTable,
      passwordKey: props.passwordKeyAlias,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
      logLevel: props.logLevel,
    });

    // DELETE /users
    new DeleteUsersApi(scope, 'DeleteUsers', {
      commonLayer: props.commonLayer,
      httpMethod: 'DELETE',
      multiUserTable: props.multiUserTable,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
      logLevel: props.logLevel,
    });

    // GET /roles
    new ListUsersApi(scope, 'ListUsers', {
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      multiUserTable: props.multiUserTable,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      passwordKey: props.passwordKeyAlias,
      authorizer: props.authorizer,
      logLevel: props.logLevel,
    });

    // DELETE /roles
    new DeleteRolesApi(this, 'DeleteRoles',
            <DeleteRolesApiProps>{
              router: props.routers.roles,
              commonLayer: props.commonLayer,
              multiUserTable: props.multiUserTable,
              httpMethod: 'DELETE',
              srcRoot: this.srcRoot,
              logLevel: props.logLevel,
            },
    );

  }
}
