import {aws_kms} from 'aws-cdk-lib';
import {Construct} from 'constructs';


export class AuthorizerLambda {

    public readonly passwordKeyAlias: aws_kms.IKey;


    constructor(scope: Construct, id: string) {


        const keyAlias = 'sd-extension-password-key';

        this.passwordKeyAlias = aws_kms.Alias.fromAliasName(scope, `${id}-createOrNew-passwordKey`, keyAlias);


    }


}

