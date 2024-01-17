import { CfnOutput, NestedStack } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class VtoStack extends NestedStack {

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const vpc = new ec2.Vpc(this, 'VPC', {
      maxAzs: 2,
    });

    const sg = new ec2.SecurityGroup(this, 'SecurityGroup', {
      vpc,
      description: 'Allow access to port 7860',
      securityGroupName: 'VtoSecurityGroupName',
    });

    sg.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(7860),
      'Allow inbound TCP traffic on port 7860',
    );


    const role = new iam.Role(this, 'InstanceRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });

    const commands = [
      'yum install -y python3',
      'git clone https://github.com/awslabs/stable-diffusion-aws-extension.git',
    ];

    const instance = new ec2.Instance(this, 'Instance', {
      vpc,
      instanceType: new ec2.InstanceType('t3.micro'),
      machineImage: new ec2.AmazonLinuxImage(),
      userData: ec2.UserData.custom(commands.join(' && ')),
      role: role,
    });


    const eip = new ec2.CfnEIP(this, 'EIP');


    new ec2.CfnEIPAssociation(this, 'EIPAssociation', {
      allocationId: eip.attrAllocationId,
      instanceId: instance.instanceId,
    });

    new CfnOutput(this, 'VtoIP', {
      value: eip.attrPublicIp,
      description: 'VTO IP Address',
    });

  }


}
