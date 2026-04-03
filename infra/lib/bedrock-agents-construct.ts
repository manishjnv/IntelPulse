import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface BedrockAgentsConstructProps {
  /**
   * Lambda functions for action groups
   */
  lambdaFunctions: {
    virusTotalLookup: lambda.Function;
    abuseIpDbCheck: lambda.Function;
    otxLookup: lambda.Function;
    shodanLookup: lambda.Function;
  };
}

/**
 * CDK Construct for Bedrock Agent Core multi-agent system
 * 
 * Creates:
 * - S3 bucket for MITRE ATT&CK data
 * - IAM roles for Bedrock agents
 * - Outputs for manual agent configuration
 * 
 * Note: Bedrock agents themselves need to be created manually via AWS Console or CLI
 * because CDK L1 constructs have limitations with action groups and knowledge bases.
 * 
 * Manual steps required after deployment:
 * 1. Upload MITRE ATT&CK data to S3 bucket
 * 2. Create Bedrock Knowledge Base (optional)
 * 3. Create 4 Bedrock agents via Console:
 *    - IOC Reputation Analyst (with Lambda action groups)
 *    - Threat Context Enricher (with Knowledge Base)
 *    - Risk Scorer
 *    - IntelPulse Threat Analyst (supervisor)
 * 4. Create agent alias for supervisor
 * 5. Add agent IDs to Secrets Manager
 */
export class BedrockAgentsConstruct extends Construct {
  public readonly mitreDataBucket: s3.Bucket;
  public readonly agentRoles: {
    reputationAnalyst: iam.Role;
    contextEnricher: iam.Role;
    riskScorer: iam.Role;
    supervisor: iam.Role;
  };

  constructor(scope: Construct, id: string, props: BedrockAgentsConstructProps) {
    super(scope, id);

    // Task 9.1: Create S3 bucket for MITRE ATT&CK data
    this.mitreDataBucket = new s3.Bucket(this, 'MitreDataBucket', {
      bucketName: `intelpulse-mitre-data-${cdk.Aws.ACCOUNT_ID}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      versioned: false,
    });

    // Create IAM roles for each agent
    this.agentRoles = {
      reputationAnalyst: this.createAgentRole('ReputationAnalyst', props.lambdaFunctions),
      contextEnricher: this.createAgentRole('ContextEnricher'),
      riskScorer: this.createAgentRole('RiskScorer'),
      supervisor: this.createAgentRole('Supervisor'),
    };

    // Grant S3 read access to context enricher (for MITRE data)
    this.mitreDataBucket.grantRead(this.agentRoles.contextEnricher);

    // Outputs for manual configuration
    new cdk.CfnOutput(this, 'MitreDataBucketName', {
      value: this.mitreDataBucket.bucketName,
      description: 'S3 Bucket for MITRE ATT&CK data - upload enterprise-attack.json here',
      exportName: 'IntelPulse-MitreDataBucketName',
    });

    new cdk.CfnOutput(this, 'ReputationAnalystRoleArn', {
      value: this.agentRoles.reputationAnalyst.roleArn,
      description: 'IAM Role ARN for Reputation Analyst agent',
      exportName: 'IntelPulse-ReputationAnalystRoleArn',
    });

    new cdk.CfnOutput(this, 'ContextEnricherRoleArn', {
      value: this.agentRoles.contextEnricher.roleArn,
      description: 'IAM Role ARN for Context Enricher agent',
      exportName: 'IntelPulse-ContextEnricherRoleArn',
    });

    new cdk.CfnOutput(this, 'RiskScorerRoleArn', {
      value: this.agentRoles.riskScorer.roleArn,
      description: 'IAM Role ARN for Risk Scorer agent',
      exportName: 'IntelPulse-RiskScorerRoleArn',
    });

    new cdk.CfnOutput(this, 'SupervisorRoleArn', {
      value: this.agentRoles.supervisor.roleArn,
      description: 'IAM Role ARN for Supervisor agent',
      exportName: 'IntelPulse-SupervisorRoleArn',
    });

    // Output Lambda ARNs for action group configuration
    new cdk.CfnOutput(this, 'ActionGroupLambdaArns', {
      value: JSON.stringify({
        virusTotal: props.lambdaFunctions.virusTotalLookup.functionArn,
        abuseIpDb: props.lambdaFunctions.abuseIpDbCheck.functionArn,
        otx: props.lambdaFunctions.otxLookup.functionArn,
        shodan: props.lambdaFunctions.shodanLookup.functionArn,
      }),
      description: 'Lambda ARNs for Bedrock agent action groups',
    });

    // Create a README file with instructions
    new cdk.CfnOutput(this, 'BedrockAgentsSetupInstructions', {
      value: 'See docs/BEDROCK_AGENTS_SETUP.md for manual configuration steps',
      description: 'Manual setup required for Bedrock agents',
    });
  }

  private createAgentRole(
    agentName: string,
    lambdaFunctions?: {
      virusTotalLookup: lambda.Function;
      abuseIpDbCheck: lambda.Function;
      otxLookup: lambda.Function;
      shodanLookup: lambda.Function;
    }
  ): iam.Role {
    const role = new iam.Role(this, `${agentName}Role`, {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      description: `IAM role for Bedrock ${agentName} agent`,
      roleName: `intelpulse-bedrock-${agentName.toLowerCase()}`,
    });

    // Grant Bedrock model invocation permissions
    role.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: [
          `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0`,
          `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0`,
        ],
      })
    );

    // If Lambda functions provided, grant invoke permissions (for reputation analyst)
    if (lambdaFunctions) {
      lambdaFunctions.virusTotalLookup.grantInvoke(role);
      lambdaFunctions.abuseIpDbCheck.grantInvoke(role);
      lambdaFunctions.otxLookup.grantInvoke(role);
      lambdaFunctions.shodanLookup.grantInvoke(role);
    }

    // For supervisor agent, grant permission to invoke other agents
    if (agentName === 'Supervisor') {
      role.addToPolicy(
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['bedrock:InvokeAgent'],
          resources: [`arn:aws:bedrock:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:agent/*`],
        })
      );
    }

    return role;
  }
}
