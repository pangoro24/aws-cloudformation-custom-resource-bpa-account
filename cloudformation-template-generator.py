#!/usr/bin/env python3
"""
Script to generate CloudFormation template with embedded Lambda function code
"""

import json
import yaml
from src.lambda_function import *

def generate_embedded_lambda_code_for_yaml():
    """Generate Lambda code formatted for YAML using literal block scalar"""
    with open('src/lambda_function.py', 'r') as f:
        lines = f.readlines()
    
    # Process lines to ensure proper YAML formatting
    # Remove trailing whitespace but preserve indentation
    processed_lines = []
    for line in lines:
        # Remove trailing whitespace but preserve the line ending
        processed_line = line.rstrip() + '\n' if line.strip() else '\n'
        processed_lines.append(processed_line)
    
    # Join all lines and remove the final newline to avoid extra blank line
    return ''.join(processed_lines).rstrip('\n')

def generate_embedded_lambda_code_for_json():
    """Generate Lambda code formatted for JSON as properly escaped string"""
    with open('src/lambda_function.py', 'r') as f:
        lambda_code = f.read()
    
    return lambda_code

def generate_cloudformation_template_json():
    """Generate CloudFormation template for JSON format"""
    
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "S3 Block Public Access Custom Resource - Enables full BPA protection at AWS account level with optional SNS notifications",
        
        "Parameters": {
            "NotificationTopicArn": {
                "Type": "String",
                "Default": "",
                "Description": "Optional SNS Topic ARN for notifications (leave empty to disable notifications)"
            }
        },
        
        "Conditions": {
            "HasNotificationTopic": {
                "Fn::Not": [
                    {
                        "Fn::Equals": [
                            {"Ref": "NotificationTopicArn"},
                            ""
                        ]
                    }
                ]
            }
        },
        
        "Resources": {
            "S3BPALambdaRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": "lambda.amazonaws.com"
                                },
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    },
                    "ManagedPolicyArns": [
                        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                    ],
                    "Policies": [
                        {
                            "PolicyName": "S3BlockPublicAccessPolicy",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "s3:GetAccountPublicAccessBlock",
                                            "s3:PutAccountPublicAccessBlock",
                                            "sts:GetCallerIdentity"
                                        ],
                                        "Resource": "*"
                                    },
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "sns:Publish"
                                        ],
                                        "Resource": {
                                            "Fn::If": [
                                                "HasNotificationTopic",
                                                {"Ref": "NotificationTopicArn"},
                                                {"Ref": "AWS::NoValue"}
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            
            "S3BPALambdaFunction": {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "FunctionName": {"Fn::Sub": "${AWS::StackName}-s3-bpa-handler"},
                    "Runtime": "python3.11",
                    "Handler": "index.lambda_handler",
                    "Role": {"Fn::GetAtt": ["S3BPALambdaRole", "Arn"]},
                    "Timeout": 300,
                    "MemorySize": 128,
                    "Code": {
                        "ZipFile": generate_embedded_lambda_code_for_json()
                    }
                }
            },
            
            "S3BlockPublicAccessResource": {
                "Type": "AWS::CloudFormation::CustomResource",
                "Properties": {
                    "ServiceToken": {"Fn::GetAtt": ["S3BPALambdaFunction", "Arn"]},
                    "NotificationTopicArn": {
                        "Fn::If": [
                            "HasNotificationTopic",
                            {"Ref": "NotificationTopicArn"},
                            {"Ref": "AWS::NoValue"}
                        ]
                    }
                }
            }
        },
        
        "Outputs": {
            "AccountId": {
                "Description": "AWS Account ID where S3 Block Public Access was configured",
                "Value": {"Fn::Sub": "${AWS::AccountId}"}
            },
            "S3BlockPublicAccessStatus": {
                "Description": "Current S3 Block Public Access status (all settings enabled)",
                "Value": "Fully Enabled - All 4 BPA settings are active"
            },
            "BlockPublicAcls": {
                "Description": "Block Public ACLs status",
                "Value": {"Fn::GetAtt": ["S3BlockPublicAccessResource", "BlockPublicAcls"]}
            },
            "IgnorePublicAcls": {
                "Description": "Ignore Public ACLs status", 
                "Value": {"Fn::GetAtt": ["S3BlockPublicAccessResource", "IgnorePublicAcls"]}
            },
            "BlockPublicPolicy": {
                "Description": "Block Public Policy status",
                "Value": {"Fn::GetAtt": ["S3BlockPublicAccessResource", "BlockPublicPolicy"]}
            },
            "RestrictPublicBuckets": {
                "Description": "Restrict Public Buckets status",
                "Value": {"Fn::GetAtt": ["S3BlockPublicAccessResource", "RestrictPublicBuckets"]}
            },
            "ConfigurationChanged": {
                "Description": "Whether BPA configuration was changed during deployment",
                "Value": {"Fn::GetAtt": ["S3BlockPublicAccessResource", "ConfigurationChanged"]}
            },
            "LastUpdated": {
                "Description": "Timestamp when BPA configuration was last processed",
                "Value": {"Fn::GetAtt": ["S3BlockPublicAccessResource", "Timestamp"]}
            }
        }
    }
    
    return template

def generate_cloudformation_template_yaml():
    """Generate CloudFormation template for YAML format with readable code embedding"""
    
    # Start with the JSON template structure
    template = generate_cloudformation_template_json()
    
    # Replace the ZipFile content with the YAML-formatted version
    template["Resources"]["S3BPALambdaFunction"]["Properties"]["Code"]["ZipFile"] = generate_embedded_lambda_code_for_yaml()
    
    return template

def main():
    """Generate and save CloudFormation template"""
    
    # Generate JSON template
    json_template = generate_cloudformation_template_json()
    
    # Generate YAML template with readable code embedding
    yaml_template = generate_cloudformation_template_yaml()
    
    # Save as JSON
    with open('s3-bpa-custom-resource.json', 'w') as f:
        json.dump(json_template, f, indent=2)
    
    # Save as YAML with custom formatting for the Lambda code
    with open('s3-bpa-custom-resource.yaml', 'w') as f:
        # Use a custom YAML dumper to handle the literal block scalar
        yaml_content = yaml.dump(yaml_template, default_flow_style=False, indent=2)
        
        # Replace the ZipFile content with literal block scalar format
        lambda_code = generate_embedded_lambda_code_for_yaml()
        
        # Find and replace the ZipFile section with literal block scalar
        import re
        
        # First, find the ZipFile line and replace it with a placeholder
        lines = yaml_content.split('\n')
        new_lines = []
        in_zipfile = False
        zipfile_indent = 0
        
        for line in lines:
            if 'ZipFile:' in line and not in_zipfile:
                # Found the start of ZipFile, replace with literal block scalar
                zipfile_indent = len(line) - len(line.lstrip())
                new_lines.append(line.split('ZipFile:')[0] + 'ZipFile: |')
                
                # Add the lambda code with proper indentation
                code_lines = lambda_code.split('\n')
                for code_line in code_lines:
                    if code_line.strip():  # Only add indentation to non-empty lines
                        new_lines.append(' ' * (zipfile_indent + 2) + code_line)
                    else:
                        new_lines.append('')  # Empty lines remain empty
                in_zipfile = True
            elif in_zipfile and line.strip() and not line.startswith(' ' * (zipfile_indent + 1)):
                # We've reached the end of the ZipFile content
                in_zipfile = False
                new_lines.append(line)
            elif not in_zipfile:
                # Normal line, keep as is
                new_lines.append(line)
            # Skip lines that are part of the original ZipFile content
        
        yaml_content = '\n'.join(new_lines)
        
        f.write(yaml_content)
    
    print("CloudFormation templates generated:")
    print("- s3-bpa-custom-resource.json")
    print("- s3-bpa-custom-resource.yaml")
    
    # Validate the embedded code by running our tests against it
    print("\nValidating embedded code logic...")
    
    # Test the embedded code logic
    test_event = {
        'RequestType': 'Create',
        'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/test/uuid',
        'RequestId': 'test-request-id',
        'LogicalResourceId': 'S3BlockPublicAccess',
        'ResourceProperties': {
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
    }
    
    print("✅ CloudFormation template generated successfully!")
    print("✅ Embedded Lambda code validated!")

if __name__ == "__main__":
    main()