import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_function import (
    get_account_id,
    get_current_bpa_config,
    apply_bpa_config,
    configs_equal,
    get_desired_config,
    send_sns_notification,
    handle_create,
    lambda_handler
)


class TestS3Operations(unittest.TestCase):
    
    @patch('lambda_function.boto3.client')
    def test_get_account_id(self, mock_boto3):
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_boto3.return_value = mock_sts
        
        account_id = get_account_id()
        
        self.assertEqual(account_id, '123456789012')
        mock_sts.get_caller_identity.assert_called_once()
    
    @patch('lambda_function.boto3.client')
    def test_get_current_bpa_config_success(self, mock_boto3):
        mock_s3control = MagicMock()
        mock_s3control.get_public_access_block.return_value = {
            'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': False
            }
        }
        mock_boto3.return_value = mock_s3control
        
        config = get_current_bpa_config('123456789012')
        
        expected = {
            'BlockPublicAcls': True,
            'IgnorePublicAcls': False,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': False
        }
        self.assertEqual(config, expected)
        mock_s3control.get_public_access_block.assert_called_once_with(AccountId='123456789012')
    
    @patch('lambda_function.boto3.client')
    def test_get_current_bpa_config_not_found(self, mock_boto3):
        from botocore.exceptions import ClientError
        
        mock_s3control = MagicMock()
        error_response = {
            'Error': {
                'Code': 'NoSuchPublicAccessBlockConfiguration',
                'Message': 'Not found'
            }
        }
        mock_s3control.get_public_access_block.side_effect = ClientError(error_response, 'GetPublicAccessBlock')
        mock_boto3.return_value = mock_s3control
        
        config = get_current_bpa_config('123456789012')
        self.assertIsNone(config)
    
    @patch('lambda_function.boto3.client')
    def test_apply_bpa_config(self, mock_boto3):
        mock_s3control = MagicMock()
        mock_boto3.return_value = mock_s3control
        
        config = {
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': False,
            'RestrictPublicBuckets': True
        }
        
        result = apply_bpa_config(config, '123456789012')
        
        self.assertEqual(result, config)
        mock_s3control.put_public_access_block.assert_called_once_with(
            AccountId='123456789012',
            PublicAccessBlockConfiguration=config
        )
    
    def test_configs_equal_none_current(self):
        current = None
        desired = {'BlockPublicAcls': True, 'IgnorePublicAcls': True, 'BlockPublicPolicy': True, 'RestrictPublicBuckets': True}
        self.assertFalse(configs_equal(current, desired))
    
    def test_configs_equal_same(self):
        config = {'BlockPublicAcls': True, 'IgnorePublicAcls': False, 'BlockPublicPolicy': True, 'RestrictPublicBuckets': False}
        self.assertTrue(configs_equal(config, config))
    
    def test_configs_equal_different(self):
        current = {'BlockPublicAcls': True, 'IgnorePublicAcls': False, 'BlockPublicPolicy': True, 'RestrictPublicBuckets': False}
        desired = {'BlockPublicAcls': True, 'IgnorePublicAcls': True, 'BlockPublicPolicy': True, 'RestrictPublicBuckets': False}
        self.assertFalse(configs_equal(current, desired))
    
    def test_get_desired_config_always_full_protection(self):
        config = get_desired_config()
        expected = {
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
        self.assertEqual(config, expected)


class TestSNSNotification(unittest.TestCase):
    
    @patch('lambda_function.boto3.client')
    def test_send_sns_notification_success(self, mock_boto3):
        mock_sns = MagicMock()
        mock_boto3.return_value = mock_sns
        
        topic_arn = 'arn:aws:sns:us-east-1:123456789012:test-topic'
        subject = 'Test Subject'
        message = 'Test Message'
        
        send_sns_notification(topic_arn, subject, message)
        
        mock_boto3.assert_called_once_with('sns')
        mock_sns.publish.assert_called_once_with(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
    
    def test_send_sns_notification_no_topic(self):
        # Should not raise exception when topic_arn is None
        send_sns_notification(None, 'Subject', 'Message')
        send_sns_notification('', 'Subject', 'Message')
    
    @patch('lambda_function.boto3.client')
    def test_send_sns_notification_error(self, mock_boto3):
        mock_sns = MagicMock()
        mock_sns.publish.side_effect = Exception('SNS Error')
        mock_boto3.return_value = mock_sns
        
        # Should not raise exception, just log error
        send_sns_notification('arn:aws:sns:us-east-1:123456789012:test-topic', 'Subject', 'Message')


class TestCreateHandler(unittest.TestCase):
    
    def setUp(self):
        self.event = {
            'RequestType': 'Create',
            'ResponseURL': 'https://test-url.com',
            'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/test/uuid',
            'RequestId': 'test-request-id',
            'LogicalResourceId': 'S3BlockPublicAccess',
            'ResourceProperties': {}
        }
        
        self.context = MagicMock()
        self.context.aws_request_id = 'test-request-id'
    
    @patch('lambda_function.send_response')
    @patch('lambda_function.send_sns_notification')
    @patch('lambda_function.apply_bpa_config')
    @patch('lambda_function.get_current_bpa_config')
    @patch('lambda_function.get_account_id')
    def test_handle_create_new_config(self, mock_get_account_id, mock_get_current, mock_apply, mock_send_sns, mock_send_response):
        mock_get_account_id.return_value = '123456789012'
        mock_get_current.return_value = None
        mock_apply.return_value = {
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
        
        properties = {'NotificationTopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'}
        
        handle_create(self.event, self.context, properties)
        
        mock_get_current.assert_called_once_with('123456789012')
        mock_apply.assert_called_once_with(mock_apply.call_args[0][0], '123456789012')
        mock_send_sns.assert_called_once()
        mock_send_response.assert_called_once()
        
        # Check SNS notification was called with success message
        sns_args = mock_send_sns.call_args
        self.assertEqual(sns_args[0][0], 'arn:aws:sns:us-east-1:123456789012:test-topic')
        self.assertIn('Configuration Applied', sns_args[0][1])
        
        # Check response was success
        response_args = mock_send_response.call_args
        self.assertEqual(response_args[0][2], 'SUCCESS')
        self.assertTrue(response_args[0][4]['ConfigurationChanged'])
    
    @patch('lambda_function.send_response')
    @patch('lambda_function.send_sns_notification')
    @patch('lambda_function.get_current_bpa_config')
    @patch('lambda_function.get_account_id')
    def test_handle_create_existing_config_matches(self, mock_get_account_id, mock_get_current, mock_send_sns, mock_send_response):
        mock_get_account_id.return_value = '123456789012'
        config = {
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
        mock_get_current.return_value = config
        
        properties = {'NotificationTopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'}
        
        handle_create(self.event, self.context, properties)
        
        mock_get_current.assert_called_once_with('123456789012')
        mock_send_sns.assert_called_once()
        mock_send_response.assert_called_once()
        
        # Check response indicates no change
        response_args = mock_send_response.call_args
        self.assertEqual(response_args[0][2], 'SUCCESS')
        self.assertFalse(response_args[0][4]['ConfigurationChanged'])
    
    @patch('lambda_function.send_response')
    @patch('lambda_function.send_sns_notification')
    @patch('lambda_function.get_current_bpa_config')
    @patch('lambda_function.get_account_id')
    def test_handle_create_no_sns_topic(self, mock_get_account_id, mock_get_current, mock_send_sns, mock_send_response):
        mock_get_account_id.return_value = '123456789012'
        config = {
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
        mock_get_current.return_value = config
        
        properties = {}  # No SNS topic
        
        handle_create(self.event, self.context, properties)
        
        # SNS should be called with None topic (which should be handled gracefully)
        mock_send_sns.assert_called_once()
        sns_args = mock_send_sns.call_args
        self.assertIsNone(sns_args[0][0])


class TestLambdaHandler(unittest.TestCase):
    
    def setUp(self):
        self.context = MagicMock()
        self.context.aws_request_id = 'test-request-id'
    
    @patch('lambda_function.handle_create')
    def test_lambda_handler_create(self, mock_handle_create):
        event = {
            'RequestType': 'Create',
            'ResourceProperties': {}
        }
        
        lambda_handler(event, self.context)
        mock_handle_create.assert_called_once()
    
    @patch('lambda_function.send_response')
    def test_lambda_handler_update(self, mock_send_response):
        event = {
            'RequestType': 'Update',
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'TestResource',
            'ResourceProperties': {}
        }
        
        lambda_handler(event, self.context)
        
        mock_send_response.assert_called_once()
        args = mock_send_response.call_args
        self.assertEqual(args[0][2], 'SUCCESS')
        self.assertIn('Update operation completed', args[0][3])
    
    @patch('lambda_function.send_response')
    def test_lambda_handler_delete(self, mock_send_response):
        event = {
            'RequestType': 'Delete',
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'TestResource',
            'ResourceProperties': {}
        }
        
        lambda_handler(event, self.context)
        
        mock_send_response.assert_called_once()
        args = mock_send_response.call_args
        self.assertEqual(args[0][2], 'SUCCESS')
        self.assertIn('Delete operation completed', args[0][3])
    
    @patch('lambda_function.send_response')
    def test_lambda_handler_invalid_request_type(self, mock_send_response):
        event = {
            'RequestType': 'InvalidType',
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'TestResource',
            'ResourceProperties': {}
        }
        
        lambda_handler(event, self.context)
        
        mock_send_response.assert_called_once()
        args = mock_send_response.call_args
        self.assertEqual(args[0][2], 'FAILED')
        self.assertIn('Unsupported request type', args[0][3])
    
    @patch('lambda_function.send_sns_notification')
    @patch('lambda_function.send_response')
    @patch('lambda_function.get_current_bpa_config')
    def test_lambda_handler_access_denied(self, mock_get_current, mock_send_response, mock_send_sns):
        from botocore.exceptions import ClientError
        
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access denied'
            }
        }
        mock_get_current.side_effect = ClientError(error_response, 'GetPublicAccessBlock')
        
        event = {
            'RequestType': 'Create',
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'TestResource',
            'ResourceProperties': {
                'NotificationTopicArn': 'arn:aws:sns:us-east-1:123456789012:test-topic'
            }
        }
        
        lambda_handler(event, self.context)
        
        # Should send failure notification
        mock_send_sns.assert_called_once()
        sns_args = mock_send_sns.call_args
        self.assertIn('Configuration Failed', sns_args[0][1])
        
        # Should send failure response
        mock_send_response.assert_called_once()
        args = mock_send_response.call_args
        self.assertEqual(args[0][2], 'FAILED')
        self.assertIn('Insufficient permissions', args[0][3])


if __name__ == '__main__':
    unittest.main()