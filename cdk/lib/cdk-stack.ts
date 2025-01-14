import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface CdkStackProps extends cdk.StackProps {
  keyPairName?: string;
}

export class CdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: CdkStackProps) {
    super(scope, id, props);

    // 使用默认 VPC
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVPC', { isDefault: true });

    // 创建安全组
    const securityGroup = new ec2.SecurityGroup(this, 'GradioSecurityGroup', {
      vpc,
      description: 'Allow inbound traffic for Gradio',
      allowAllOutbound: true,
    });

    // 允许入站规则: 端口 22 (SSH) 和 7860 (Gradio)
    securityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(22),
      'Allow SSH access'
    );
    securityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(7860),
      'Allow Gradio web access'
    );

    // 创建 IAM 角色
    const role = new iam.Role(this, 'GradioRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      roleName: 'gradio_demo',
    });

    // 添加所需的 AWS 服务权限
    role.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonBedrockFullAccess')
    );
    role.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonRekognitionFullAccess')
    );
    role.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonTranscribeFullAccess')
    );
    role.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('ComprehendFullAccess')
    );

    // 使用硬编码的密钥对名称
    const keyPair = ec2.KeyPair.fromKeyPairName(this, 'InstanceKeyPair', 'us-west-2-linux');

    // 创建 EC2 实例并分配 IAM 角色
    const instance = new ec2.Instance(this, 'GradioInstance', {
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      securityGroup,
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.LARGE),
      machineImage: new ec2.AmazonLinuxImage({
        generation: ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023,
      }),
      role,
      keyPair,
      blockDevices: [{
        deviceName: '/dev/xvda', // 根卷的设备名称
        volume: ec2.BlockDeviceVolume.ebs(30, { // 30 GiB
          volumeType: ec2.EbsDeviceVolumeType.GP3,
          encrypted: true,
        }),
      }],
    });

    // 添加用户数据脚本
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      'yum update -y',
      'yum install -y git',
      'yum install -y python3.11-devel mesa-libGL', // Required for opencv
      'cd /home/ec2-user',
      'git clone https://github.com/xdstone1on163/llm_content_moderation_demo_with_gradio.git',
      'cd llm_content_moderation_demo_with_gradio',
      'dnf install python3.11 -y',
      'dnf install python3.11-pip -y',
      'pip3.11 install -r requirements.txt',
      'nohup python3.11 main.py &',
    );
    instance.addUserData(userData.render());

    // 创建并关联弹性 IP
    const eip = new ec2.CfnEIP(this, 'GradioEIP', {
      domain: 'vpc',
      instanceId: instance.instanceId,
    });

    // 输出实例公共 IP、弹性 IP 和 Gradio URL
    new cdk.CfnOutput(this, 'InstancePublicIP', {
      value: instance.instancePublicIp,
      description: 'Public IP of the EC2 instance',
    });
    new cdk.CfnOutput(this, 'ElasticIP', {
      value: eip.ref,
      description: 'Elastic IP address',
    });
    new cdk.CfnOutput(this, 'GradioURL', {
      value: `http://${eip.ref}:7860`,
      description: 'URL for accessing Gradio interface',
    });
  }
}
