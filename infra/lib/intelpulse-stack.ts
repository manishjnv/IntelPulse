import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';
import { readFileSync } from 'fs';
import { join } from 'path';

export class IntelPulseStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly securityGroups: {
    alb: ec2.SecurityGroup;
    ecs: ec2.SecurityGroup;
    postgres: ec2.SecurityGroup;
    redis: ec2.SecurityGroup;
    opensearch: ec2.SecurityGroup;
  };
  public readonly timescaleDbInstance: ec2.Instance;
  public readonly redisCluster: elasticache.CfnCacheCluster;
  public readonly opensearchDomain: opensearch.Domain;
  public readonly ecrRepositories: {
    api: ecr.Repository;
    ui: ecr.Repository;
    worker: ecr.Repository;
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
    this.timescaleDbInstance = this.createTimescaleDbInstance();

    // Task 4: ElastiCache Redis and OpenSearch
    this.redisCluster = this.createRedisCluster();
    this.opensearchDomain = this.createOpenSearchDomain();

    // Task 5: ECR repositories
    this.ecrRepositories = this.createEcrRepositories();

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

  private createTimescaleDbInstance(): ec2.Instance {
    // Create IAM role for EC2 instance
    const role = new iam.Role(this, 'TimescaleDbInstanceRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      description: 'IAM role for TimescaleDB EC2 instance',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });

    // User data script to install Docker and run TimescaleDB
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      '#!/bin/bash',
      'set -e',
      '',
      '# Update system',
      'yum update -y',
      '',
      '# Install Docker',
      'yum install -y docker',
      'systemctl start docker',
      'systemctl enable docker',
      'usermod -a -G docker ec2-user',
      '',
      '# Create data directory',
      'mkdir -p /data/postgres',
      'chmod 777 /data/postgres',
      '',
      '# Generate random password for PostgreSQL',
      'POSTGRES_PASSWORD=$(openssl rand -base64 32)',
      'echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" > /root/.postgres_password',
      'chmod 600 /root/.postgres_password',
      '',
      '# Run TimescaleDB container',
      'docker run -d \\',
      '  --name timescaledb \\',
      '  --restart unless-stopped \\',
      '  -p 5432:5432 \\',
      '  -e POSTGRES_DB=intelpulse \\',
      '  -e POSTGRES_USER=intelpulse \\',
      '  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \\',
      '  -v /data/postgres:/var/lib/postgresql/data \\',
      '  timescale/timescaledb:latest-pg16',
      '',
      '# Wait for PostgreSQL to be ready',
      'echo "Waiting for PostgreSQL to start..."',
      'sleep 30',
      '',
      '# Store connection info in SSM Parameter Store',
      'aws ssm put-parameter \\',
      '  --name "/intelpulse/production/postgres-password" \\',
      '  --value "${POSTGRES_PASSWORD}" \\',
      '  --type "SecureString" \\',
      '  --overwrite \\',
      `  --region ${this.region}`,
      '',
      'echo "TimescaleDB setup complete!"',
    );

    // Get Amazon Linux 2023 AMI
    const ami = ec2.MachineImage.latestAmazonLinux2023({
      cpuType: ec2.AmazonLinuxCpuType.X86_64,
    });

    // Create EC2 instance
    const instance = new ec2.Instance(this, 'TimescaleDbInstance', {
      vpc: this.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        availabilityZones: [this.vpc.availabilityZones[0]], // First AZ only
      },
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        ec2.InstanceSize.MEDIUM
      ),
      machineImage: ami,
      securityGroup: this.securityGroups.postgres,
      role: role,
      userData: userData,
      blockDevices: [
        {
          deviceName: '/dev/xvda',
          volume: ec2.BlockDeviceVolume.ebs(50, {
            volumeType: ec2.EbsDeviceVolumeType.GP3,
            encrypted: true,
            deleteOnTermination: false, // Preserve data on instance termination
          }),
        },
      ],
      userDataCausesReplacement: true,
    });

    // Add permission to write to SSM Parameter Store
    instance.role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:PutParameter'],
        resources: [
          `arn:aws:ssm:${this.region}:${this.account}:parameter/intelpulse/production/*`,
        ],
      })
    );

    // Tag instance
    cdk.Tags.of(instance).add('Name', 'intelpulse-timescaledb');

    // Output instance details
    new cdk.CfnOutput(this, 'TimescaleDbInstanceId', {
      value: instance.instanceId,
      description: 'TimescaleDB EC2 Instance ID',
      exportName: 'IntelPulse-TimescaleDbInstanceId',
    });

    new cdk.CfnOutput(this, 'TimescaleDbPrivateIp', {
      value: instance.instancePrivateIp,
      description: 'TimescaleDB Private IP Address',
      exportName: 'IntelPulse-TimescaleDbPrivateIp',
    });

    new cdk.CfnOutput(this, 'TimescaleDbConnectionString', {
      value: `postgresql://intelpulse:[PASSWORD]@${instance.instancePrivateIp}:5432/intelpulse`,
      description: 'TimescaleDB Connection String (retrieve password from SSM Parameter Store: /intelpulse/production/postgres-password)',
      exportName: 'IntelPulse-TimescaleDbConnectionString',
    });

    return instance;
  }

  private createRedisCluster(): elasticache.CfnCacheCluster {
    // Create subnet group for ElastiCache
    const subnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
      description: 'Subnet group for IntelPulse Redis cluster',
      subnetIds: this.vpc.privateSubnets.map(subnet => subnet.subnetId),
      cacheSubnetGroupName: 'intelpulse-redis-subnet-group',
    });

    // Create Redis cluster
    const cluster = new elasticache.CfnCacheCluster(this, 'RedisCluster', {
      cacheNodeType: 'cache.t3.micro',
      engine: 'redis',
      engineVersion: '7.0',
      numCacheNodes: 1,
      clusterName: 'intelpulse-redis',
      cacheSubnetGroupName: subnetGroup.cacheSubnetGroupName,
      vpcSecurityGroupIds: [this.securityGroups.redis.securityGroupId],
      port: 6379,
      preferredMaintenanceWindow: 'sun:05:00-sun:06:00',
      snapshotRetentionLimit: 5,
      snapshotWindow: '03:00-04:00',
      tags: [
        { key: 'Name', value: 'intelpulse-redis' },
        { key: 'Project', value: 'IntelPulse' },
        { key: 'Environment', value: 'production' },
      ],
    });

    cluster.addDependency(subnetGroup);

    // Output Redis endpoint
    new cdk.CfnOutput(this, 'RedisEndpoint', {
      value: cluster.attrRedisEndpointAddress,
      description: 'Redis Cluster Endpoint Address',
      exportName: 'IntelPulse-RedisEndpoint',
    });

    new cdk.CfnOutput(this, 'RedisPort', {
      value: cluster.attrRedisEndpointPort,
      description: 'Redis Cluster Port',
      exportName: 'IntelPulse-RedisPort',
    });

    return cluster;
  }

  private createOpenSearchDomain(): opensearch.Domain {
    // Create OpenSearch domain
    const domain = new opensearch.Domain(this, 'OpenSearchDomain', {
      version: opensearch.EngineVersion.OPENSEARCH_2_13,
      domainName: 'intelpulse-opensearch',
      capacity: {
        dataNodes: 1,
        dataNodeInstanceType: 't3.small.search',
        multiAzWithStandbyEnabled: false, // Explicitly disable Multi-AZ for T3 instances
      },
      ebs: {
        volumeSize: 20,
        volumeType: ec2.EbsDeviceVolumeType.GP3,
      },
      vpc: this.vpc,
      vpcSubnets: [
        {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          availabilityZones: [this.vpc.availabilityZones[0]], // First AZ only
        },
      ],
      securityGroups: [this.securityGroups.opensearch],
      zoneAwareness: {
        enabled: false, // Single-node deployment
      },
      enforceHttps: true,
      nodeToNodeEncryption: true,
      encryptionAtRest: {
        enabled: true,
      },
      // Fine-grained access control disabled for simplicity
      fineGrainedAccessControl: {
        masterUserArn: undefined,
      },
      // Use unsigned requests (VPC-based security)
      useUnsignedBasicAuth: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For development/testing
    });

    // Output OpenSearch endpoint
    new cdk.CfnOutput(this, 'OpenSearchEndpoint', {
      value: domain.domainEndpoint,
      description: 'OpenSearch Domain Endpoint',
      exportName: 'IntelPulse-OpenSearchEndpoint',
    });

    new cdk.CfnOutput(this, 'OpenSearchDomainArn', {
      value: domain.domainArn,
      description: 'OpenSearch Domain ARN',
      exportName: 'IntelPulse-OpenSearchDomainArn',
    });

    return domain;
  }

  private createEcrRepositories(): {
    api: ecr.Repository;
    ui: ecr.Repository;
    worker: ecr.Repository;
  } {
    // Create ECR repository for API
    const apiRepo = new ecr.Repository(this, 'ApiRepository', {
      repositoryName: 'intelpulse/api',
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.MUTABLE,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For development/testing
      lifecycleRules: [
        {
          description: 'Keep last 10 images',
          maxImageCount: 10,
        },
      ],
    });

    // Create ECR repository for UI
    const uiRepo = new ecr.Repository(this, 'UiRepository', {
      repositoryName: 'intelpulse/ui',
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.MUTABLE,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      lifecycleRules: [
        {
          description: 'Keep last 10 images',
          maxImageCount: 10,
        },
      ],
    });

    // Create ECR repository for Worker
    const workerRepo = new ecr.Repository(this, 'WorkerRepository', {
      repositoryName: 'intelpulse/worker',
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.MUTABLE,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      lifecycleRules: [
        {
          description: 'Keep last 10 images',
          maxImageCount: 10,
        },
      ],
    });

    // Output repository URIs
    new cdk.CfnOutput(this, 'ApiRepositoryUri', {
      value: apiRepo.repositoryUri,
      description: 'ECR Repository URI for API',
      exportName: 'IntelPulse-ApiRepositoryUri',
    });

    new cdk.CfnOutput(this, 'UiRepositoryUri', {
      value: uiRepo.repositoryUri,
      description: 'ECR Repository URI for UI',
      exportName: 'IntelPulse-UiRepositoryUri',
    });

    new cdk.CfnOutput(this, 'WorkerRepositoryUri', {
      value: workerRepo.repositoryUri,
      description: 'ECR Repository URI for Worker',
      exportName: 'IntelPulse-WorkerRepositoryUri',
    });

    return {
      api: apiRepo,
      ui: uiRepo,
      worker: workerRepo,
    };
  }
}
