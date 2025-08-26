# Design Document

## Overview

Diseño optimizado para un CloudFormation Custom Resource que gestiona S3 Block Public Access a nivel de cuenta de AWS y envía notificaciones SNS. Se ejecuta solo durante CREATE del stack.

## Architecture

### Components

1. **CloudFormation Custom Resource**: Definición del recurso personalizado
2. **Lambda Function**: Función que maneja solo operaciones CREATE
3. **IAM Role**: Rol con permisos para S3 BPA y SNS
4. **SNS Topic**: Topic para notificaciones de éxito/fallo

### Lambda Function Design

#### Core Functions

- `get_current_bpa_config()`: Obtiene configuración actual de BPA
- `apply_bpa_config(config)`: Aplica nueva configuración de BPA
- `configs_equal(current, desired)`: Compara configuraciones para idempotencia
- `send_sns_notification()`: Envía notificaciones a SNS topic
- `handle_create()`: Manejador principal para CREATE operations
- `send_response()`: Envía respuesta a CloudFormation

#### Event Processing

```python
{
  "RequestType": "Create|Update|Delete",
  "ResponseURL": "https://cloudformation-custom-resource-response-...",
  "StackId": "arn:aws:cloudformation:...",
  "RequestId": "unique-id",
  "LogicalResourceId": "S3BlockPublicAccess",
  "ResourceProperties": {
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true,
    "NotificationTopicArn": "arn:aws:sns:region:account:topic"
  }
}
```

#### Operation Logic

- **CREATE**: Aplica configuración BPA y envía notificación SNS
- **UPDATE**: Retorna SUCCESS sin cambios (no se requiere lógica)
- **DELETE**: Retorna SUCCESS sin cambios (no se requiere lógica)

#### SNS Notification Format

```json
{
  "Status": "SUCCESS|FAILED",
  "Message": "Operation result message",
  "Configuration": {
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  },
  "ConfigurationChanged": true,
  "Timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Handling

### Error Types

1. **AWS API Errors**: AccessDenied, NoSuchPublicAccessBlockConfiguration
2. **SNS Errors**: Topic not found, insufficient permissions
3. **Internal Errors**: Unexpected exceptions

### Error Response Strategy

- Map AWS API errors to user-friendly messages
- Send failure notifications to SNS if configured
- Return FAILED status with descriptive reason
- Log errors for troubleshooting

## Security

### IAM Permissions

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
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:*"
    }
  ]
}
```

### Security Considerations

- Minimal IAM permissions (S3 BPA + SNS publish)
- SNS notifications optional (graceful degradation)
- CloudWatch logging for audit trail
- No sensitive data in notifications