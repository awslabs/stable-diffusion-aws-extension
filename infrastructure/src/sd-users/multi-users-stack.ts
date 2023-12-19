import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_apigateway,
  aws_dynamodb,
  aws_kms,
  NestedStack,
  StackProps,
} from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Construct } from 'constructs';
import { RoleUpsertApi } from './role-upsert-api';
import { ListAllRolesApi } from './roles-listall-api';
import { UserDeleteApi } from './user-delete-api';
import { UserUpsertApi } from './user-upsert-api';
import { ListAllUsersApi } from './users-listall-api';
import {DeleteRolesApi, DeleteRolesApiProps} from "../api/roles/delete-roles";


export interface MultiUsersStackProps extends StackProps {
  multiUserTable: aws_dynamodb.Table;
  routers: {[key: string]: Resource};
  commonLayer: PythonLayerVersion;
  useExist: string;
  passwordKeyAlias: aws_kms.IKey;
  authorizer: aws_apigateway.IAuthorizer;
}

export class MultiUsersStack extends NestedStack {
  private readonly srcRoot='../middleware_api/lambda';

  constructor(scope: Construct, id: string, props: MultiUsersStackProps) {
    super(scope, id, props);

    new RoleUpsertApi(scope, 'roleUpsert', {
      commonLayer: props.commonLayer,
      httpMethod: 'POST',
      multiUserTable: props.multiUserTable,
      router: props.routers.roles,
      srcRoot: this.srcRoot,
    });

    new ListAllRolesApi(scope, 'roleListAll', {
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      multiUserTable: props.multiUserTable,
      router: props.routers.roles,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
    });

    new UserUpsertApi(scope, 'CreateUser', {
      commonLayer: props.commonLayer,
      httpMethod: 'POST',
      multiUserTable: props.multiUserTable,
      passwordKey: props.passwordKeyAlias,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
    });

    new UserDeleteApi(scope, 'DeleteUsers', {
      commonLayer: props.commonLayer,
      httpMethod: 'DELETE',
      multiUserTable: props.multiUserTable,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
    });

    new ListAllUsersApi(scope, 'ListUsers', {
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      multiUserTable: props.multiUserTable,
      router: props.routers.users,
      srcRoot: this.srcRoot,
      passwordKey: props.passwordKeyAlias,
      authorizer: props.authorizer,
    });

    new DeleteRolesApi(
        this, 'DeleteRoles',
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
