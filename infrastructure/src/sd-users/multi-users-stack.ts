import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_kms, NestedStack, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Construct } from 'constructs';
import { CreateRoleApi } from '../api/roles/create-role';
import { DeleteRolesApi, DeleteRolesApiProps } from '../api/roles/delete-roles';
import { ListRolesApi } from '../api/roles/list-roles';
import { CreateUserApi } from '../api/users/create-user';
import { DeleteUsersApi } from '../api/users/delete-users';
import { ListUsersApi } from '../api/users/list-users';


export interface MultiUsersStackProps extends StackProps {
  multiUserTable: aws_dynamodb.Table;
  routers: { [key: string]: Resource };
  commonLayer: PythonLayerVersion;
  useExist: string;
  passwordKeyAlias: aws_kms.IKey;
  authorizer: aws_apigateway.IAuthorizer;
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
    });

    // GET /roles
    new ListRolesApi(scope, 'ListRoles', {
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      multiUserTable: props.multiUserTable,
      router: props.routers.roles,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
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
    });

    // DELETE /users
    new DeleteUsersApi(scope, 'DeleteUsers', {
      commonLayer: props.commonLayer,
      httpMethod: 'DELETE',
      multiUserTable: props.multiUserTable,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
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
    });

    // DELETE /roles
    new DeleteRolesApi(this, 'DeleteRoles',
            <DeleteRolesApiProps>{
              router: props.routers.roles,
              commonLayer: props.commonLayer,
              multiUserTable: props.multiUserTable,
              httpMethod: 'DELETE',
              srcRoot: this.srcRoot,
            },
    );

  }
}
