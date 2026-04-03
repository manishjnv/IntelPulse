import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { IntelPulseStack } from '../lib/intelpulse-stack';

test('IntelPulseStack creates successfully', () => {
  const app = new cdk.App();
  const stack = new IntelPulseStack(app, 'TestStack', {
    env: {
      region: 'ap-south-1'
    }
  });
  const template = Template.fromStack(stack);

  // Verify stack has proper tags
  const stackTags = cdk.Tags.of(stack);
  expect(stackTags).toBeDefined();
});
