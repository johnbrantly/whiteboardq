"""Self-signed certificate generation for TLS support."""

import ipaddress
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate_self_signed_cert(
    hostname: str,
    output_dir: Path,
    days_valid: int = 365,
) -> tuple[Path, Path]:
    """
    Generate a self-signed certificate for the WhiteboardQ server.

    Args:
        hostname: Server hostname or IP address
        output_dir: Directory to save cert.pem and key.pem
        days_valid: Certificate validity period

    Returns:
        Tuple of (cert_path, key_path)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "cert.pem"
    key_path = output_dir / "key.pem"

    # Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Build certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WhiteboardQ"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])

    # Subject Alternative Names - include hostname and localhost
    san_list = [x509.DNSName(hostname), x509.DNSName("localhost")]

    # Add IP address if hostname looks like one
    try:
        ip = ipaddress.ip_address(hostname)
        san_list.append(x509.IPAddress(ip))
    except ValueError:
        pass

    # Always add localhost IP
    san_list.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))

    # Build certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=days_valid))
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    # Write private key
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    # Write certificate
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    logger.info(f"Generated self-signed certificate:")
    logger.info(f"  Certificate: {cert_path}")
    logger.info(f"  Private key: {key_path}")
    logger.info(f"  Valid for: {days_valid} days")
    logger.info(f"  Hostname: {hostname}")

    return cert_path, key_path
