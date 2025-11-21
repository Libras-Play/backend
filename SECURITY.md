# Security Policy

## 🔒 Reporting a Vulnerability

We take the security of LibrasPlay seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### ⚠️ Please DO NOT:
- Open a public GitHub issue for security vulnerabilities
- Disclose the vulnerability publicly before it has been addressed
- Test vulnerabilities on production systems without permission

### ✅ Please DO:
- Report security vulnerabilities privately via email
- Provide detailed steps to reproduce the vulnerability
- Give us reasonable time to address the issue before public disclosure

---

## 📧 Contact

**Security Email**: security@librasplay.com

**Response Time**: We aim to acknowledge your report within 48 hours

**PGP Key**: [Available on request]

---

## 📝 What to Include in Your Report

Please include as much information as possible:

1. **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass)
2. **Affected component(s)** (e.g., content-service, user-service, API endpoint)
3. **Steps to reproduce** the vulnerability
4. **Proof of concept** (PoC) if available
5. **Potential impact** of the vulnerability
6. **Suggested remediation** (if you have ideas)
7. **Your contact information** for follow-up questions

### Example Report Format

```
Subject: [SECURITY] SQL Injection in /api/v1/users endpoint

Description:
The /api/v1/users endpoint is vulnerable to SQL injection when the
'filter' parameter is not properly sanitized.

Affected Component:
- user-service v1.2.3
- Endpoint: GET /api/v1/users?filter=...

Steps to Reproduce:
1. Send request: GET /api/v1/users?filter=' OR '1'='1
2. Observe SQL error in response
3. Exploit allows extracting user data

Proof of Concept:
[Include curl command or screenshot]

Impact:
- Unauthorized access to user data
- Potential database compromise
- CVSS Score: 8.5 (High)

Suggested Fix:
Use parameterized queries in user_service.py line 123
```

---

## 🕐 Disclosure Timeline

We follow **Coordinated Vulnerability Disclosure**:

1. **Day 0**: You report the vulnerability
2. **Day 1-2**: We acknowledge receipt
3. **Day 3-7**: We validate and assess severity
4. **Day 8-30**: We develop and test a fix
5. **Day 31-45**: We deploy the fix to production
6. **Day 46-90**: Public disclosure (if appropriate)

We will keep you updated throughout the process.

---

## 🏆 Recognition

We appreciate the security community's help in keeping LibrasPlay safe!

### Hall of Fame

Security researchers who have responsibly disclosed vulnerabilities:

- *[No vulnerabilities reported yet]*

### Acknowledgment Options

If you report a valid security vulnerability, we offer:

- **Public acknowledgment** in our Hall of Fame (optional)
- **CVE credit** if applicable
- **Swag** for significant findings (t-shirt, stickers)
- **Reference letter** for security researchers (on request)

We currently do **not offer a bug bounty program** but appreciate all responsible disclosures.

---

## 🔐 Supported Versions

We support security updates for the following versions:

| Version | Supported          | End of Support |
| ------- | ------------------ | -------------- |
| 1.x.x   | ✅ Yes (current)   | TBD            |
| 0.x.x   | ❌ No (deprecated) | 2025-01-01     |

**Recommendation**: Always use the latest stable version.

---

## 🛡️ Security Best Practices for Contributors

If you're contributing to LibrasPlay, please follow these security guidelines:

### Code Security
- ✅ Never commit secrets, API keys, or passwords
- ✅ Use parameterized queries (prevent SQL injection)
- ✅ Validate and sanitize all user inputs
- ✅ Use AWS Secrets Manager for production credentials
- ✅ Enable HTTPS/TLS for all communications
- ✅ Implement rate limiting on APIs
- ✅ Use strong authentication (OAuth, Cognito)

### Dependency Security
- ✅ Regularly update dependencies (`pip list --outdated`)
- ✅ Use `pip-audit` or `safety` to check for vulnerabilities
- ✅ Pin dependency versions in `requirements.txt`
- ✅ Review dependency licenses

### Infrastructure Security
- ✅ Enable encryption at rest (RDS, DynamoDB, S3)
- ✅ Enable encryption in transit (TLS 1.2+)
- ✅ Use VPC private subnets for services
- ✅ Apply least-privilege IAM policies
- ✅ Enable CloudTrail for audit logging
- ✅ Configure security groups restrictively
- ✅ Use AWS Secrets Manager (not environment variables)

### Testing Security
- ✅ Run security linters: `bandit`, `semgrep`
- ✅ Scan Docker images: `trivy`, `snyk`
- ✅ Test authentication and authorization
- ✅ Perform OWASP Top 10 checks
- ✅ Conduct penetration testing before major releases

---

## 🚨 Known Security Measures

LibrasPlay implements the following security controls:

### Application Layer
- **Authentication**: AWS Cognito with MFA support
- **Authorization**: Role-based access control (RBAC)
- **Input Validation**: Pydantic models for all API inputs
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **XSS Prevention**: FastAPI automatic escaping
- **CSRF Protection**: SameSite cookies, CORS configuration
- **Rate Limiting**: API throttling per user/IP
- **Session Management**: JWT tokens with expiration

### Infrastructure Layer
- **Network Isolation**: Private VPC subnets for services
- **Encryption at Rest**: RDS (AES-256), DynamoDB, S3
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Secrets Management**: AWS Secrets Manager (not env vars)
- **Monitoring**: CloudWatch logs, GuardDuty, Security Hub
- **Access Control**: IAM roles with least privilege
- **Backup**: Automated RDS backups, DynamoDB point-in-time recovery

### CI/CD Security
- **Code Scanning**: GitHub CodeQL, Dependabot
- **Image Scanning**: ECR scans all Docker images
- **Secret Detection**: git-secrets, TruffleHog
- **SAST**: Static analysis in CI pipeline
- **DAST**: Dynamic testing in staging environment

---

## 📚 Security Resources

### OWASP Top 10 (2021)
We actively protect against:
1. ✅ Broken Access Control
2. ✅ Cryptographic Failures
3. ✅ Injection
4. ✅ Insecure Design
5. ✅ Security Misconfiguration
6. ✅ Vulnerable Components
7. ✅ Authentication Failures
8. ✅ Software/Data Integrity Failures
9. ✅ Logging/Monitoring Failures
10. ✅ Server-Side Request Forgery (SSRF)

### Compliance
- **LGPD** (Brazil): User data protection compliance
- **GDPR** (EU): Data privacy for European users
- **COPPA** (US): Child protection compliance

---

## 🔄 Security Update Process

### Critical Vulnerabilities (CVSS 9.0-10.0)
- **Response Time**: Within 24 hours
- **Patch Deployment**: Within 48 hours
- **Notification**: Immediate email to all users

### High Vulnerabilities (CVSS 7.0-8.9)
- **Response Time**: Within 48 hours
- **Patch Deployment**: Within 7 days
- **Notification**: Security advisory posted

### Medium Vulnerabilities (CVSS 4.0-6.9)
- **Response Time**: Within 7 days
- **Patch Deployment**: Within 30 days
- **Notification**: Included in release notes

### Low Vulnerabilities (CVSS 0.1-3.9)
- **Response Time**: Within 14 days
- **Patch Deployment**: Next scheduled release
- **Notification**: Included in release notes

---

## 📞 Emergency Contact

For **active security incidents** (e.g., ongoing attack, data breach):

1. **Email**: security@librasplay.com (mark as URGENT)
2. **Subject**: `[SECURITY INCIDENT] Brief description`
3. **Include**: What's happening, affected systems, current impact

We monitor this email 24/7 for critical incidents.

---

## ⚖️ Legal

**Responsible Disclosure Agreement**:
- We will not pursue legal action against researchers who follow this policy
- We ask that you do not access, modify, or delete user data
- We ask that you do not disrupt our services
- We ask that you give us reasonable time to fix issues

**Safe Harbor**: We consider security research conducted in accordance with this policy to be:
- Authorized under the Computer Fraud and Abuse Act (CFAA)
- Exempt from DMCA anti-circumvention provisions
- Lawful and not in violation of our Terms of Service

---

## 📜 Version History

| Version | Date       | Changes |
|---------|------------|---------|
| 1.0     | 2025-11-20 | Initial security policy |

---

## 📬 Questions?

If you have questions about this security policy:
- Email: security@librasplay.com
- GitHub Discussions: https://github.com/librasplay/backend/discussions

---

**Last Updated**: 2025-11-20  
**Next Review**: 2026-02-20

Thank you for helping keep LibrasPlay secure! 🛡️
