#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { IntelPulseStack } from '../lib/intelpulse-stack';

const app = new cdk.App();

new IntelPulseStack(app, 'IntelPulseStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-east-1'
  },
  description: 'IntelPulse Threat Intelligence Platform - AWS Infrastructure',
  tags: {
    Project: 'IntelPulse',
    Environment: 'production',
    ManagedBy: 'CDK'
  }
});
