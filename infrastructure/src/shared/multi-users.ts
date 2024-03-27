import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_dynamodb, aws_kms, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Construct } from 'constructs';
import { KEY_ALIAS } from './const';
import { CreateRoleApi } from '../api/roles/create-role';
import { DeleteRolesApi } from '../api/roles/delete-roles';
import { ListRolesApi } from '../api/roles/list-roles';
import { CreateUserApi } from '../api/users/create-user';
import { DeleteUsersApi } from '../api/users/delete-users';
import { ListUsersApi } from '../api/users/list-users';


export interface MultiUsersStackProps extends StackProps {
  multiUserTable: aws_dynamodb.Table;
  routers: { [key: string]: Resource };
  commonLayer: PythonLayerVersion;
}

export class MultiUsers {
  private readonly srcRoot: string = '../middleware_api/lambda';
  private readonly passwordKeyAlias: aws_kms.IKey;

  constructor(scope: Construct, props: MultiUsersStackProps) {

    this.passwordKeyAlias = aws_kms.Alias.fromAliasName(
      scope,
      'sd-authorizer-createOrNew-passwordKey',
      KEY_ALIAS,
    );

    // POST /roles
    const createRoleApi = new CreateRoleApi(scope, 'CreateRole', {
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
    });

    // POST /users
    const createUserApi = new CreateUserApi(scope, 'CreateUser', {
      commonLayer: props.commonLayer,
      httpMethod: 'POST',
      multiUserTable: props.multiUserTable,
      passwordKey: this.passwordKeyAlias,
      router: props.routers.users,
      srcRoot: this.srcRoot,
    });
    createUserApi.model.node.addDependency(createRoleApi.model);
    createUserApi.requestValidator.node.addDependency(createRoleApi.requestValidator);

    // DELETE /users
    const deleteUsersApi = new DeleteUsersApi(scope, 'DeleteUsers', {
      commonLayer: props.commonLayer,
      httpMethod: 'DELETE',
      multiUserTable: props.multiUserTable,
      router: props.routers.users,
      srcRoot: this.srcRoot,
    });
    deleteUsersApi.model.node.addDependency(createUserApi.model);
    deleteUsersApi.requestValidator.node.addDependency(createUserApi.requestValidator);

    // GET /roles
    new ListUsersApi(scope, 'ListUsers', {
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      multiUserTable: props.multiUserTable,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      passwordKey: this.passwordKeyAlias,
    });

    // DELETE /roles
    const deleteRolesApi = new DeleteRolesApi(scope, 'DeleteRoles', {
      router: props.routers.roles,
      commonLayer: props.commonLayer,
      multiUserTable: props.multiUserTable,
      httpMethod: 'DELETE',
      srcRoot: this.srcRoot,
    },
    );
    deleteRolesApi.model.node.addDependency(deleteUsersApi.model);
    deleteRolesApi.requestValidator.node.addDependency(deleteUsersApi.requestValidator);

  }
}
