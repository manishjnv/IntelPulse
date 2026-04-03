import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export class IntelPulseStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly securityGroups: {
    alb: ec2.SecurityGroup;
    ecs: ec2.SecurityGroup;
    postgres: ec2.SecurityGroup;
    redis: ec2.SecurityGroup;
    opensearch: ec2.SecurityGroup;
  };

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Tag all resources in this stack
    cdk.Tags.of(this).add('Project', 'IntelPulse');
    cdk.Tags.of(this).add('Environment', 'production');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');

    // Task 2: VPC and networking
    this.vpc = this.createVpc();
    this.securityGroups = this.createSecurityGroups();

    // Task 3: EC2 for TimescaleDB
    // Task 4: ElastiCache Redis and OpenSearch
    // Task 5: ECR repositories
    // Task 6: ECS Fargate cluster and services
  }

  private createVpc(): ec2.Vpc {
    // Create VPC with 2 AZs, public and private subnets with explicit CIDR blocks
    const vpc = new ec2.Vpc(this, 'IntelPulseVpc', {
      vpcName: 'intelpulse-vpc',
      ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
      maxAzs: 2,
      natGateways: 1, // Single NAT Gateway for cost optimization
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
          mapPublicIpOnLaunch: true,
        },
        {
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
      ],
    });

    // Output VPC ID
    new cdk.CfnOutput(this, 'VpcId', {
      value: vpc.vpcId,
      description: 'VPC ID',
      exportName: 'IntelPulse-VpcId',
    });

    // Output subnet IDs
    new cdk.CfnOutput(this, 'PublicSubnetIds', {
      value: vpc.publicSubnets.map(subnet => subnet.subnetId).join(','),
      description: 'Public Subnet IDs (10.0.0.0/24, 10.0.1.0/24)',
      exportName: 'IntelPulse-PublicSubnetIds',
    });

    new cdk.CfnOutput(this, 'PrivateSubnetIds', {
      value: vpc.privateSubnets.map(subnet => subnet.subnetId).join(','),
      description: 'Private Subnet IDs (10.0.2.0/24, 10.0.3.0/24)',
      exportName: 'IntelPulse-PrivateSubnetIds',
    });

    return vpc;
  }

  private createSecurityGroups(): {
    alb: ec2.SecurityGroup;
    ecs: ec2.SecurityGroup;
    postgres: ec2.SecurityGroup;
    redis: ec2.SecurityGroup;
    opensearch: ec2.SecurityGroup;
  } {
    // Security Group for ALB
    const albSg = new ec2.SecurityGroup(this, 'AlbSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: 'intelpulse-sg-alb',
      description: 'Security group for Application Load Balancer',
      allowAllOutbound: true,
    });

    // ALB: Allow HTTP and HTTPS from anywhere
    albSg.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'Allow HTTP from anywhere'
    );
    albSg.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow HTTPS from anywhere'
    );

    // Security Group for ECS tasks
    const ecsSg = new ec2.SecurityGroup(this, 'EcsSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: 'intelpulse-sg-ecs',
      description: 'Security group for ECS Fargate tasks',
      allowAllOutbound: true,
    });

    // ECS: Allow traffic from ALB on ports 3000 (UI) and 8000 (API)
    ecsSg.addIngressRule(
      albSg,
      ec2.Port.tcp(3000),
      'Allow UI traffic from ALB'
    );
    ecsSg.addIngressRule(
      albSg,
      ec2.Port.tcp(8000),
      'Allow API traffic from ALB'
    );

    // Security Group for PostgreSQL/TimescaleDB
    const postgresSg = new ec2.SecurityGroup(this, 'PostgresSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: 'intelpulse-sg-postgres',
      description: 'Security group for TimescaleDB on EC2',
      allowAllOutbound: false,
    });

    // PostgreSQL: Allow connections from ECS tasks only
    postgresSg.addIngressRule(
      ecsSg,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL from ECS tasks'
    );

    // Security Group for Redis
    const redisSg = new ec2.SecurityGroup(this, 'RedisSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: 'intelpulse-sg-redis',
      description: 'Security group for ElastiCache Redis',
      allowAllOutbound: false,
    });

    // Redis: Allow connections from ECS tasks only
    redisSg.addIngressRule(
      ecsSg,
      ec2.Port.tcp(6379),
      'Allow Redis from ECS tasks'
    );

    // Security Group for OpenSearch
    const opensearchSg = new ec2.SecurityGroup(this, 'OpenSearchSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: 'intelpulse-sg-opensearch',
      description: 'Security group for OpenSearch Service',
      allowAllOutbound: false,
    });

    // OpenSearch: Allow HTTPS connections from ECS tasks only
    opensearchSg.addIngressRule(
      ecsSg,
      ec2.Port.tcp(443),
      'Allow HTTPS from ECS tasks'
    );

    // Output security group IDs
    new cdk.CfnOutput(this, 'AlbSecurityGroupId', {
      value: albSg.securityGroupId,
      description: 'ALB Security Group ID',
      exportName: 'IntelPulse-AlbSecurityGroupId',
    });

    new cdk.CfnOutput(this, 'EcsSecurityGroupId', {
      value: ecsSg.securityGroupId,
      description: 'ECS Security Group ID',
      exportName: 'IntelPulse-EcsSecurityGroupId',
    });

    new cdk.CfnOutput(this, 'PostgresSecurityGroupId', {
      value: postgresSg.securityGroupId,
      description: 'PostgreSQL Security Group ID',
      exportName: 'IntelPulse-PostgresSecurityGroupId',
    });

    new cdk.CfnOutput(this, 'RedisSecurityGroupId', {
      value: redisSg.securityGroupId,
      description: 'Redis Security Group ID',
      exportName: 'IntelPulse-RedisSecurityGroupId',
    });

    new cdk.CfnOutput(this, 'OpenSearchSecurityGroupId', {
      value: opensearchSg.securityGroupId,
      description: 'OpenSearch Security Group ID',
      exportName: 'IntelPulse-OpenSearchSecurityGroupId',
    });

    return {
      alb: albSg,
      ecs: ecsSg,
      postgres: postgresSg,
      redis: redisSg,
      opensearch: opensearchSg,
    };
  }
}
