# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within CertDeliver, please send an email to the maintainer. All security vulnerabilities will be promptly addressed.

**Please do not disclose security vulnerabilities publicly until they have been handled by the maintainers.**

### What to include in your report

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Release**: Depending on severity, typically within 14-30 days

## Security Best Practices

When deploying CertDeliver:

1. **Use strong tokens**: Generate random tokens with at least 32 characters
2. **Restrict network access**: Use firewall rules to limit access to the server
3. **Enable HTTPS**: Always use TLS for server communication
4. **Keep updated**: Regularly update to the latest version
5. **Monitor logs**: Review server logs for suspicious activity
