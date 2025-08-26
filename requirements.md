# Requirements Document

## Introduction

Este documento define los requisitos para un CloudFormation Custom Resource simple que habilita S3 Block Public Access a nivel de cuenta de AWS y envía notificación SNS. La solución se ejecuta una sola vez durante el CREATE del stack.

## Requirements

### Requirement 1: S3 Block Public Access Configuration

**User Story:** As a security engineer, I want to enable S3 Block Public Access at the account level through CloudFormation.

#### Acceptance Criteria

1. WHEN the CloudFormation template is deployed THEN the system SHALL enable all four BPA settings by default
2. WHEN the Custom Resource is created THEN the system SHALL apply BPA configuration to the account
3. WHEN BPA settings are already configured THEN the system SHALL update them to match desired state
4. IF the account lacks permissions THEN the system SHALL return a FAILED status with error message

### Requirement 2: SNS Notification

**User Story:** As an operations engineer, I want to receive notifications when BPA configuration is applied.

#### Acceptance Criteria

1. WHEN BPA configuration is applied successfully THEN the system SHALL send success notification to SNS topic
2. WHEN BPA configuration fails THEN the system SHALL send failure notification to SNS topic
3. WHEN SNS topic ARN is not provided THEN the system SHALL skip notification without failing
4. WHEN SNS notification fails THEN the system SHALL log error but not fail the main operation

### Requirement 3: Simple CloudFormation Template

**User Story:** As a DevOps engineer, I want a single CloudFormation template that contains everything needed.

#### Acceptance Criteria

1. WHEN the template is deployed THEN the system SHALL create a Lambda function with embedded Python code
2. WHEN the Lambda function executes THEN the system SHALL process only CREATE operations
3. WHEN UPDATE or DELETE events occur THEN the system SHALL return SUCCESS without changes
4. WHEN deployment fails THEN the system SHALL provide error messages

### Requirement 4: Minimal Permissions

**User Story:** As a security architect, I want the Custom Resource to use minimum required permissions.

#### Acceptance Criteria

1. WHEN the Lambda executes THEN the system SHALL use only required S3 and SNS permissions
2. WHEN the Lambda processes requests THEN the system SHALL log operations to CloudWatch
3. IF the Lambda role lacks permissions THEN the system SHALL return FAILED status