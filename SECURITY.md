# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

- **Sensitive issues**: Email [john@johnbrantly.com](mailto:john@johnbrantly.com) with details. Please allow reasonable time for a fix before public disclosure.
- **General bugs**: Open a [GitHub Issue](https://github.com/johnbrantly/whiteboardq/issues).

## Scope

WhiteboardQ is designed for use on trusted local area networks (LANs). It is not intended to be exposed to the public internet.

## TLS Certificates

WhiteboardQ auto-generates self-signed TLS certificates on first run. These encrypt traffic but do not provide identity verification. For production environments requiring trusted certificates, replace the generated files in `%ProgramData%\WhiteboardQ\certs\` with certificates from a trusted CA.

## Disclaimer

This software is provided as-is under the [GPL v3.0](LICENSE). Use at your own risk.
