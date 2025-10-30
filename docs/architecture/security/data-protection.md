# Data Protection

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines data protection strategies for the Task Management System, including encryption at rest and in transit, secrets management, PII handling, data anonymization, and GDPR compliance mechanisms.

---

## Data Protection Principles

### Core Principles

1. **Defense in Depth**: Multiple layers of protection
2. **Encryption Everywhere**: Data encrypted at rest and in transit
3. **Minimal Data Retention**: Keep only what's necessary
4. **Privacy by Design**: Privacy built into architecture
5. **Data Sovereignty**: Respect regional data laws

---

## Encryption at Rest

### Database Encryption (AWS RDS)

**Technology**: AWS RDS Encryption using AWS KMS

**Configuration**:

```yaml
RDS Instance:
  StorageEncrypted: true
  KmsKeyId: arn:aws:kms:us-east-1:123456789:key/abc-123
  Encryption Algorithm: AES-256

Automated Backups:
  Encrypted: true
  KmsKeyId: Same as instance

Read Replicas:
  Encrypted: true
  KmsKeyId: Same as primary
```

**Key Rotation**: Automatic annual rotation via AWS KMS

**Performance Impact**: < 3% overhead for encryption/decryption

### File Storage Encryption (S3)

**Technology**: AWS S3 Server-Side Encryption (SSE-KMS)

```yaml
S3 Bucket:
  Encryption:
    Type: aws:kms
    KMSMasterKeyID: arn:aws:kms:us-east-1:123456789:key/def-456
  Versioning: Enabled
  PublicAccessBlock: All blocked
```

**Implementation**:

```python
import boto3

class S3StorageService:
    """Encrypted file storage in S3"""

    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'taskmanager-attachments'
        self.kms_key_id = 'arn:aws:kms:us-east-1:123456789:key/def-456'

    def upload_file(
        self,
        file_content: bytes,
        file_path: str,
        content_type: str
    ) -> str:
        """Upload file with encryption"""
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=file_path,
            Body=file_content,
            ContentType=content_type,
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=self.kms_key_id,
            # Additional security
            ACL='private',
            Metadata={
                'uploaded-by': 'taskmanager-api',
                'encryption': 'kms'
            }
        )

        return f"s3://{self.bucket_name}/{file_path}"

    def generate_presigned_url(
        self,
        file_path: str,
        expiration: int = 3600
    ) -> str:
        """Generate temporary download URL"""
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': file_path
            },
            ExpiresIn=expiration  # 1 hour default
        )
        return url
```

### Application-Level Encryption

**Use Case**: Sensitive fields requiring additional encryption beyond database encryption.

**Fields**: Credit card numbers, SSN, sensitive PII

**Technology**: Fernet (symmetric encryption) via AWS KMS data keys

```python
from cryptography.fernet import Fernet
import boto3
import base64

class FieldEncryptionService:
    """Encrypt sensitive database fields"""

    def __init__(self):
        self.kms_client = boto3.client('kms')
        self.kms_key_id = 'arn:aws:kms:us-east-1:123456789:key/ghi-789'
        self._cipher = None

    def _get_cipher(self) -> Fernet:
        """Get or create Fernet cipher with KMS data key"""
        if not self._cipher:
            # Generate data key from KMS
            response = self.kms_client.generate_data_key(
                KeyId=self.kms_key_id,
                KeySpec='AES_256'
            )

            # Use plaintext key for encryption (kept in memory)
            key = base64.urlsafe_b64encode(response['Plaintext'])
            self._cipher = Fernet(key)

        return self._cipher

    def encrypt(self, plaintext: str) -> str:
        """Encrypt sensitive data"""
        cipher = self._get_cipher()
        encrypted = cipher.encrypt(plaintext.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt sensitive data"""
        cipher = self._get_cipher()
        decrypted = cipher.decrypt(base64.b64decode(ciphertext))
        return decrypted.decode()

# Usage in model
class PaymentMethod:
    """Payment method with encrypted card number"""

    def __init__(self, encryption_service: FieldEncryptionService):
        self.encryption = encryption_service
        self._card_number_encrypted = None

    @property
    def card_number(self) -> str:
        """Decrypt card number"""
        if self._card_number_encrypted:
            return self.encryption.decrypt(self._card_number_encrypted)
        return None

    @card_number.setter
    def card_number(self, value: str) -> None:
        """Encrypt card number"""
        self._card_number_encrypted = self.encryption.encrypt(value)
```

---

## Encryption in Transit

### TLS Configuration

**Requirements**:

- TLS 1.3 (primary)
- TLS 1.2 (fallback for legacy clients)
- TLS 1.0/1.1 DISABLED

**Certificate**: AWS Certificate Manager (ACM) with auto-renewal

```yaml
Load Balancer Configuration:
  Protocol: HTTPS
  Port: 443
  SSL Policy: ELBSecurityPolicy-TLS-1-2-Ext-2018-06
  Certificate: arn:aws:acm:us-east-1:123456789:certificate/xyz-abc

  SSL Ciphers (Allowed):
    - TLS_AES_128_GCM_SHA256
    - TLS_AES_256_GCM_SHA384
    - TLS_CHACHA20_POLY1305_SHA256

  SSL Ciphers (Blocked):
    - All export ciphers
    - All weak ciphers (< 128-bit)
    - All anonymous ciphers
```

### Database Connections

**RDS MySQL**: TLS required for all connections

```python
from sqlalchemy import create_engine

DATABASE_URL = "mysql+pymysql://user:pass@host:3306/db"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        'ssl': {
            'ssl_ca': '/path/to/rds-ca-bundle.pem',
            'ssl_verify_cert': True,
            'ssl_verify_identity': True
        }
    }
)
```

### API Client Requirements

```python
from fastapi import FastAPI, Request
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# Force HTTPS
app.add_middleware(HTTPSRedirectMiddleware)

# Strict Transport Security
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

---

## Secrets Management

### AWS Secrets Manager

**Storage**: All secrets in AWS Secrets Manager (not environment variables)

**Secrets Stored**:

- Database credentials
- JWT signing key
- OAuth client secrets
- API keys for third-party services
- Encryption keys

**Configuration**:

```yaml
Secrets:
  - Name: taskmanager/prod/database
    Value:
      username: admin
      password: <auto-generated-32-char>
      host: db.example.com
      port: 3306
    Rotation: 90 days

  - Name: taskmanager/prod/jwt-secret
    Value: <256-bit-secret>
    Rotation: 180 days

  - Name: taskmanager/prod/oauth-google
    Value:
      client_id: <client-id>
      client_secret: <secret>
    Rotation: Manual (when regenerated)
```

**Implementation**:

```python
import boto3
import json
from functools import lru_cache

class SecretsService:
    """Retrieve secrets from AWS Secrets Manager"""

    def __init__(self):
        self.client = boto3.client('secretsmanager', region_name='us-east-1')
        self.cache_ttl = 300  # 5 minutes

    @lru_cache(maxsize=10)
    def get_secret(self, secret_name: str) -> dict:
        """Retrieve and cache secret"""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_value = json.loads(response['SecretString'])
            return secret_value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise

    def get_database_credentials(self) -> dict:
        """Get database credentials"""
        return self.get_secret('taskmanager/prod/database')

    def get_jwt_secret(self) -> str:
        """Get JWT signing secret"""
        secret = self.get_secret('taskmanager/prod/jwt-secret')
        return secret['secret_key']

# Usage in application startup
secrets_service = SecretsService()
db_creds = secrets_service.get_database_credentials()

DATABASE_URL = f"mysql+pymysql://{db_creds['username']}:{db_creds['password']}@{db_creds['host']}/{db_creds['database']}"
```

### Secret Rotation

**Automated Rotation**: Database passwords rotated every 90 days

```python
import boto3

def rotate_database_password(secret_arn: str, token: str):
    """AWS Lambda function for secret rotation"""
    secrets_client = boto3.client('secretsmanager')
    rds_client = boto3.client('rds')

    # Get current secret
    current_secret = secrets_client.get_secret_value(SecretId=secret_arn)
    current_creds = json.loads(current_secret['SecretString'])

    # Generate new password
    new_password = secrets_client.get_random_password(
        PasswordLength=32,
        ExcludeCharacters='"\'@/\\'
    )['RandomPassword']

    # Update RDS password
    rds_client.modify_db_instance(
        DBInstanceIdentifier=current_creds['dbname'],
        MasterUserPassword=new_password,
        ApplyImmediately=True
    )

    # Update secret
    current_creds['password'] = new_password
    secrets_client.put_secret_value(
        SecretId=secret_arn,
        SecretString=json.dumps(current_creds),
        VersionStages=['AWSCURRENT']
    )
```

---

## PII Handling

### PII Classification

| Data Type        | PII Level | Encryption   | Retention        | GDPR Article |
| ---------------- | --------- | ------------ | ---------------- | ------------ |
| **Email**        | High      | At rest      | Account lifetime | Art. 6, 17   |
| **Full Name**    | High      | At rest      | Account lifetime | Art. 6, 17   |
| **IP Address**   | Medium    | At rest      | 12 months        | Art. 6, 17   |
| **User Agent**   | Low       | At rest      | 12 months        | Art. 6       |
| **Task Content** | Medium    | At rest      | Account lifetime | Art. 6, 17   |
| **Comments**     | Medium    | At rest      | Account lifetime | Art. 6, 17   |
| **Attachments**  | Medium    | At rest + S3 | Account lifetime | Art. 6, 17   |

### PII Protection Implementation

```python
from dataclasses import dataclass
from enum import Enum

class PIILevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

@dataclass
class PIIField:
    """PII field metadata"""
    field_name: str
    pii_level: PIILevel
    encryption_required: bool
    anonymize_after_days: int
    gdpr_article: str

# PII registry
PII_REGISTRY = {
    'email': PIIField('email', PIILevel.HIGH, True, None, 'Art. 6, 17'),
    'full_name': PIIField('full_name', PIILevel.HIGH, True, None, 'Art. 6, 17'),
    'ip_address': PIIField('ip_address', PIILevel.MEDIUM, True, 365, 'Art. 6, 17'),
    'user_agent': PIIField('user_agent', PIILevel.LOW, True, 365, 'Art. 6'),
}

class PIIService:
    """Handle PII operations"""

    def anonymize_old_data(self):
        """Anonymize PII after retention period"""
        cutoff_date = datetime.utcnow() - timedelta(days=365)

        # Anonymize old audit logs
        old_logs = db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).all()

        for log in old_logs:
            log.ip_address = self._anonymize_ip(log.ip_address)
            log.user_agent = '[ANONYMIZED]'

        db.commit()
        logger.info(f"Anonymized {len(old_logs)} audit logs")

    def _anonymize_ip(self, ip_address: str) -> str:
        """Anonymize IP address (keep network, zero host)"""
        # IPv4: 192.168.1.100 → 192.168.0.0
        parts = ip_address.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.0.0"
        return '[ANONYMIZED]'
```

---

## GDPR Compliance

### Right to Access (Article 15)

**Implementation**: Export all user data in JSON format

```python
class DataExportService:
    """Export user data for GDPR compliance"""

    def export_user_data(self, user_id: UUID) -> dict:
        """Export all user data"""
        user = self.user_repo.get_by_id(user_id)

        # Collect all user data
        data = {
            'personal_information': {
                'user_id': str(user.user_id),
                'email': user.email,
                'full_name': user.full_name,
                'created_at': user.created_at.isoformat(),
                'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None
            },
            'projects': [
                p.to_dict() for p in self.project_repo.list_by_user(user_id)
            ],
            'tasks': [
                t.to_dict() for t in self.task_repo.list_by_user(user_id)
            ],
            'comments': [
                c.to_dict() for c in self.comment_repo.list_by_user(user_id)
            ],
            'audit_logs': [
                log.to_dict() for log in self.audit_repo.list_by_user(user_id)
            ]
        }

        return data
```

### Right to Erasure (Article 17)

**Implementation**: Delete or anonymize user data

```python
class DataDeletionService:
    """Handle data deletion requests"""

    def delete_user_data(self, user_id: UUID) -> dict:
        """Delete user and associated data"""
        user = self.user_repo.get_by_id(user_id)

        # 1. Soft delete user account
        user.status = "DELETED"
        user.email = f"deleted_{user_id}@deleted.local"
        user.full_name = "[DELETED USER]"
        user.password_hash = None
        user.deleted_at = datetime.utcnow()
        self.user_repo.save(user)

        # 2. Anonymize task assignments (keep task history)
        tasks = self.task_repo.list_by_user(user_id)
        for task in tasks:
            if task.assignee_id == user_id:
                task.assignee_id = None
            if task.created_by == user_id:
                task.created_by = None  # Or keep for audit

        # 3. Anonymize comments
        comments = self.comment_repo.list_by_user(user_id)
        for comment in comments:
            comment.author_id = None
            comment.content = "[Comment by deleted user]"

        # 4. Anonymize audit logs after retention period
        self.pii_service.anonymize_old_data()

        # 5. Delete OAuth tokens
        self.auth_service.revoke_all_tokens(user_id)

        # 6. Delete file attachments
        attachments = self.attachment_repo.list_by_user(user_id)
        for attachment in attachments:
            self.s3_service.delete_file(attachment.file_path)

        return {
            'user_id': str(user_id),
            'deleted_at': datetime.utcnow().isoformat(),
            'data_deleted': {
                'projects': len(tasks),
                'comments': len(comments),
                'attachments': len(attachments)
            }
        }
```

### Data Processing Agreement

**Required for GDPR Article 28**

```yaml
Data Processing Agreement (DPA):
  Controller: [Customer Organization]
  Processor: TaskManager SaaS

  Scope:
    - Personal data types: Email, name, IP address, task content
    - Purpose: Provide task management services
    - Duration: Duration of subscription

  Security Measures:
    - Encryption: At rest (AES-256), in transit (TLS 1.3)
    - Access Control: RBAC, MFA for admins
    - Backup: Daily encrypted backups, 30-day retention
    - Audit: Comprehensive logging, 12-month retention

  Sub-Processors:
    - AWS: Infrastructure hosting (us-east-1, eu-west-1)
    - SendGrid: Email delivery

  Data Subject Rights:
    - Access: Export within 30 days
    - Erasure: Delete within 30 days
    - Portability: JSON/CSV export
```

---

## Data Anonymization

### Anonymization Techniques

```python
class AnonymizationService:
    """Anonymize or pseudonymize data"""

    def anonymize_email(self, email: str) -> str:
        """Replace email with hash"""
        import hashlib
        hash_value = hashlib.sha256(email.encode()).hexdigest()[:16]
        return f"anon_{hash_value}@anonymized.local"

    def pseudonymize_user_id(self, user_id: UUID) -> str:
        """Generate consistent pseudonym"""
        import hashlib
        hash_value = hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
        return f"user_{hash_value}"

    def anonymize_ip_address(self, ip: str) -> str:
        """Zero out last octet"""
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        return "[ANONYMIZED]"
```

---

## Security Best Practices

### DO ✅

1. **Encrypt All Data at Rest**: RDS, S3, Redis
2. **Use TLS 1.3**: For all network communication
3. **Store Secrets in Secrets Manager**: Never in code/config
4. **Rotate Secrets Regularly**: Every 90 days minimum
5. **Classify PII**: Know what data needs protection
6. **Anonymize Old Data**: After retention period
7. **Provide Data Export**: GDPR Article 15 compliance

### DON'T ❌

1. **Don't Store Passwords**: Only bcrypt hashes
2. **Don't Log Sensitive Data**: PII, secrets, tokens
3. **Don't Use Weak Encryption**: AES-256 minimum
4. **Don't Hard-Code Secrets**: Use Secrets Manager
5. **Don't Keep Data Forever**: Define retention policies
6. **Don't Ignore Data Subject Requests**: Legal requirement
7. **Don't Mix Encrypted/Unencrypted**: Consistent protection

---

## Related Documents

- [Authentication](./authentication.md)
- [Authorization](./authorization.md)
- [Audit Logging](./audit-logging.md)
- [OWASP Compliance](./owasp-compliance.md)

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)
