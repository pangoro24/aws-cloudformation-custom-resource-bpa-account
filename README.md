# AWS S3 Block Public Access Custom Resource

A simplified CloudFormation Custom Resource for managing S3 Block Public Access settings at the AWS account level.

Read more in dev.to: https://dev.to/pangoro24/cloudformation-custom-resources-en-espanol-sencillo-1p17


## Quick Start

### Basic Deployment (No Notifications)

```bash
aws cloudformation create-stack \
  --stack-name s3-block-public-access \
  --template-body file://s3-bpa-custom-resource.yaml \
  --capabilities CAPABILITY_IAM
```

### Deployment with SNS Notifications

```bash
aws cloudformation create-stack \
  --stack-name s3-block-public-access \
  --template-body file://s3-bpa-custom-resource.yaml \
  --capabilities CAPABILITY_IAM \
  --parameters ParameterKey=NotificationTopicArn,ParameterValue=arn:aws:sns:us-east-1:123456789012:s3-bpa-notifications
```

### Check Deployment Status

```bash
aws cloudformation describe-stacks \
  --stack-name s3-block-public-access \
  --query 'Stacks[0].StackStatus'
```

### View Results

```bash
aws cloudformation describe-stacks \
  --stack-name s3-block-public-access \
  --query 'Stacks[0].Outputs'
```

## Template Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `NotificationTopicArn` | `""` | Optional SNS Topic ARN for notifications |

**Note**: The Custom Resource automatically enables all 4 Block Public Access settings for maximum security. No configuration parameters are needed.

## SNS Notifications

When you provide a `NotificationTopicArn`, the Custom Resource will send notifications for:

### Success Notifications
- **Configuration Applied**: When BPA settings are successfully updated
- **No Change Required**: When current settings already match desired configuration

### Failure Notifications
- **Access Denied**: When insufficient permissions to modify BPA settings
- **Unexpected Errors**: For any other failures during execution

### Notification Format

```json
{
  "Status": "SUCCESS|FAILED",
  "Message": "Descriptive message about the operation",
  "AccountId": "123456789012",
  "PreviousConfiguration": { ... },
  "NewConfiguration": { ... },
  "ConfigurationChanged": true,
  "Timestamp": "2024-01-15T10:30:00.000Z"
}
```

## What Gets Configured

The Custom Resource automatically enables **all 4 Block Public Access settings**:

- ✅ **BlockPublicAcls**: `true` - Blocks public ACLs on buckets and objects
- ✅ **IgnorePublicAcls**: `true` - Ignores public ACLs on buckets and objects  
- ✅ **BlockPublicPolicy**: `true` - Blocks public bucket policies
- ✅ **RestrictPublicBuckets**: `true` - Restricts public bucket policies

This provides **maximum security** by default with no configuration required.

## Features

- ✅ **Simple**: 192-line Lambda function, no external dependencies
- ✅ **Embedded**: Python code embedded directly in CloudFormation template
- ✅ **Secure**: Automatically enables all 4 BPA settings for maximum protection
- ✅ **Zero-Config**: No parameters needed - always applies full BPA protection
- ✅ **Idempotent**: Only applies changes when needed
- ✅ **One-time**: Only processes CREATE operations, ignores UPDATE/DELETE
- ✅ **Notifications**: Optional SNS notifications for success/failure
- ✅ **Tested**: 19 unit tests with full coverage

## How It Works

1. **CREATE**: Applies BPA configuration if different from current state
2. **UPDATE/DELETE**: Ignored for security (BPA is one-time configuration)
3. **Idempotency**: Compares current vs desired state, only updates if needed
4. **Notifications**: Sends SNS notifications for success/failure if topic provided
5. **Error Handling**: Handles AWS API errors with user-friendly messages

## Outputs

The template provides these outputs:

- `AccountId`: AWS Account ID where BPA was configured
- `S3BlockPublicAccessStatus`: Overall status message (always "Fully Enabled")
- `BlockPublicAcls`: Current Block Public ACLs setting (always `true`)
- `IgnorePublicAcls`: Current Ignore Public ACLs setting (always `true`)
- `BlockPublicPolicy`: Current Block Public Policy setting (always `true`)
- `RestrictPublicBuckets`: Current Restrict Public Buckets setting (always `true`)
- `ConfigurationChanged`: Whether the BPA configuration was changed during deployment
- `LastUpdated`: Timestamp when BPA configuration was last processed

## IAM Permissions

The Lambda function uses minimal permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetPublicAccessBlock",
        "s3:PutPublicAccessBlock",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "*"
    }
  ]
}
```

## Development

### Run Tests
```bash
python -m pytest tests/test_lambda_function.py -v
```

### Generate Templates
```bash
python cloudformation-template-generator.py
```

### Project Structure
```
├── src/lambda_function.py              # Main Lambda function (192 lines)
├── tests/test_lambda_function.py       # Unit tests (19 tests)
├── s3-bpa-custom-resource.yaml        # CloudFormation template (YAML)
├── s3-bpa-custom-resource.json        # CloudFormation template (JSON)
└── cloudformation-template-generator.py # Template generator
```

## Troubleshooting

### Common Issues

1. **AccessDenied Error**: Ensure the deployment role has permissions to create IAM roles and Lambda functions
2. **SNS Publish Failed**: Verify the SNS topic exists and allows publish from the Lambda function
3. **Stack Creation Failed**: Check CloudFormation events for detailed error messages

### Verification

Check if S3 Block Public Access is enabled:

```bash
aws s3control get-public-access-block --account-id $(aws sts get-caller-identity --query Account --output text)
```

**Note**: The Custom Resource uses the S3 Control API (`s3control`) which is the correct service for account-level Block Public Access operations.

## Cleanup

To remove the Custom Resource and clean up:

```bash
aws cloudformation delete-stack --stack-name s3-block-public-access
```

**Note**: BPA settings will be retained for security even after stack deletion.

## License

This project is provided as-is for educational and practical use.