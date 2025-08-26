import json
import logging
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import urllib3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_account_id():
    """Get AWS Account ID from STS"""
    sts_client = boto3.client('sts')
    return sts_client.get_caller_identity()['Account']

def get_current_bpa_config(account_id):
    try:
        s3control_client = boto3.client('s3control')
        response = s3control_client.get_public_access_block(AccountId=account_id)
        config = response.get('PublicAccessBlockConfiguration', {})
        return {
            'BlockPublicAcls': config.get('BlockPublicAcls', True),
            'IgnorePublicAcls': config.get('IgnorePublicAcls', True),
            'BlockPublicPolicy': config.get('BlockPublicPolicy', True),
            'RestrictPublicBuckets': config.get('RestrictPublicBuckets', True)
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
            return None
        raise

def apply_bpa_config(config, account_id):
    s3control_client = boto3.client('s3control')
    s3control_client.put_public_access_block(
        AccountId=account_id,
        PublicAccessBlockConfiguration=config
    )
    return config

def configs_equal(current, desired):
    if current is None:
        return False
    return (current['BlockPublicAcls'] == desired['BlockPublicAcls'] and
            current['IgnorePublicAcls'] == desired['IgnorePublicAcls'] and
            current['BlockPublicPolicy'] == desired['BlockPublicPolicy'] and
            current['RestrictPublicBuckets'] == desired['RestrictPublicBuckets'])

def get_desired_config():
    """Always return full BPA configuration - all settings enabled for maximum security"""
    return {
        'BlockPublicAcls': True,
        'IgnorePublicAcls': True,
        'BlockPublicPolicy': True,
        'RestrictPublicBuckets': True
    }

def send_sns_notification(topic_arn, subject, message):
    if not topic_arn:
        return
    
    try:
        sns_client = boto3.client('sns')
        sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        logger.info(f"SNS notification sent to {topic_arn}")
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {str(e)}")

def send_response(event, context, status, reason, data=None):
    response_body = {
        'Status': status,
        'Reason': reason,
        'PhysicalResourceId': event.get('PhysicalResourceId', f"account-bpa-{context.aws_request_id}"),
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId']
    }
    
    if data:
        response_body['Data'] = data
    
    response_url = event['ResponseURL']
    
    try:
        http = urllib3.PoolManager()
        response = http.request('PUT', response_url, 
                              body=json.dumps(response_body),
                              headers={'Content-Type': 'application/json'})
        logger.info(f"Response sent: {response.status}")
    except Exception as e:
        logger.error(f"Failed to send response: {str(e)}")

def handle_create(event, context, properties):
    logger.info("Handling CREATE operation - applying full S3 Block Public Access")
    
    account_id = get_account_id()
    desired_config = get_desired_config()  # Always full BPA protection
    current_config = get_current_bpa_config(account_id)
    topic_arn = properties.get('NotificationTopicArn')
    
    if configs_equal(current_config, desired_config):
        logger.info("S3 Block Public Access already fully enabled")
        config_changed = False
        final_config = current_config
        message = "S3 Block Public Access already fully enabled at account level"
    else:
        logger.info("Enabling full S3 Block Public Access protection")
        final_config = apply_bpa_config(desired_config, account_id)
        config_changed = True
        message = "S3 Block Public Access fully enabled at account level"
    
    data = {
        'BlockPublicAcls': final_config['BlockPublicAcls'],
        'IgnorePublicAcls': final_config['IgnorePublicAcls'],
        'BlockPublicPolicy': final_config['BlockPublicPolicy'],
        'RestrictPublicBuckets': final_config['RestrictPublicBuckets'],
        'ConfigurationChanged': config_changed,
        'Timestamp': datetime.utcnow().isoformat()
    }
    
    notification_message = {
        'Status': 'SUCCESS',
        'Message': message,
        'AccountId': account_id,
        'Configuration': final_config,
        'ConfigurationChanged': config_changed,
        'Timestamp': data['Timestamp']
    }
    
    send_sns_notification(
        topic_arn,
        'S3 Block Public Access - Configuration Applied',
        json.dumps(notification_message, indent=2)
    )
    
    send_response(event, context, 'SUCCESS', message, data)

def lambda_handler(event, context):
    logger.info(f"Received {event['RequestType']} request")
    
    try:
        request_type = event['RequestType']
        properties = event.get('ResourceProperties', {})
        topic_arn = properties.get('NotificationTopicArn')
        
        if request_type == 'Create':
            handle_create(event, context, properties)
        elif request_type in ['Update', 'Delete']:
            logger.info(f"{request_type} operation - no action needed, returning success")
            data = {
                'Message': f'{request_type} operation completed - no changes made',
                'Timestamp': datetime.utcnow().isoformat()
            }
            send_response(event, context, 'SUCCESS', f'{request_type} operation completed', data)
        else:
            raise ValueError(f"Unsupported request type: {request_type}")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS API error: {error_code} - {error_message}")
        
        if error_code == 'AccessDenied':
            reason = "Insufficient permissions to modify S3 Block Public Access settings"
        else:
            reason = f"AWS API error: {error_code}"
        
        notification_message = {
            'Status': 'FAILED',
            'Error': reason,
            'ErrorCode': error_code,
            'Timestamp': datetime.utcnow().isoformat()
        }
        
        topic_arn = event.get('ResourceProperties', {}).get('NotificationTopicArn')
        send_sns_notification(
            topic_arn,
            'S3 Block Public Access - Configuration Failed',
            json.dumps(notification_message, indent=2)
        )
            
        send_response(event, context, 'FAILED', reason)
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        
        notification_message = {
            'Status': 'FAILED',
            'Error': f'Internal error: {str(e)}',
            'Timestamp': datetime.utcnow().isoformat()
        }
        
        topic_arn = event.get('ResourceProperties', {}).get('NotificationTopicArn')
        send_sns_notification(
            topic_arn,
            'S3 Block Public Access - Internal Error',
            json.dumps(notification_message, indent=2)
        )
        
        send_response(event, context, 'FAILED', f"Internal error: {str(e)}")