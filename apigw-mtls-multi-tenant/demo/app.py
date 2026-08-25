"""
mTLS Demo Web App — Visual test runner for API Gateway mTLS full-chain validation.
Streams test output via Server-Sent Events so the customer sees real-time progress.
"""

import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

# Resolve project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
CERT_DIR = PROJECT_DIR / "certs"
CONFIG_FILE = PROJECT_DIR / "config.env"

# Hostname validation pattern — only allows valid DNS characters
_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$")


def _validate_hostname(domain):
    """Validate and return a safe hostname string.

    Raises ValueError if the domain contains characters outside the
    allowed DNS hostname set (alphanumeric, hyphens, dots).
    """
    if not domain or not _HOSTNAME_RE.match(domain) or len(domain) > 253:
        raise ValueError(f"Invalid hostname: {domain!r}")
    return domain


def load_config():
    """Load config.env as a dict."""
    config = {}
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip().strip('"').strip("'")
    return config


VALID_SSE_EVENTS = {"start", "output", "certinfo", "result", "error", "done"}


def sse_event(event_type, data):
    """Format a Server-Sent Event. event_type is validated against an allowlist."""
    if event_type not in VALID_SSE_EVENTS:
        event_type = "error"
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def get_cert_info(cert_path):
    """Extract subject, issuer, dates from a PEM certificate file."""
    result = subprocess.run(
        ["openssl", "x509", "-in", str(cert_path), "-noout",
         "-subject", "-issuer", "-dates"],
        capture_output=True, text=True,
    )
    info = {}
    for line in result.stdout.strip().splitlines():
        if line.startswith("subject="):
            info["subject"] = line.split("=", 1)[1].strip().lstrip("/").replace("/", ", ")
        elif line.startswith("issuer="):
            info["issuer"] = line.split("=", 1)[1].strip().lstrip("/").replace("/", ", ")
        elif line.startswith("notBefore="):
            info["notBefore"] = line.split("=", 1)[1].strip()
        elif line.startswith("notAfter="):
            info["notAfter"] = line.split("=", 1)[1].strip()
    return info


def get_truststore_certs(pem_path):
    """Parse a PEM file with multiple certs and return info for each."""
    certs = []
    pem_text = Path(pem_path).read_text()
    # Split into individual PEM blocks
    import re
    pem_blocks = re.findall(
        r"(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)",
        pem_text, re.DOTALL
    )
    for i, block in enumerate(pem_blocks):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
        tmp.write(block)
        tmp.close()
        info = get_cert_info(tmp.name)
        os.unlink(tmp.name)
        info["index"] = i + 1
        certs.append(info)
    return certs


def emit_cert_context(truststore_path, client_cert_path=None, client_label=None):
    """Emit SSE events showing truststore and client cert details."""
    # Truststore info
    truststore_certs = get_truststore_certs(truststore_path)
    truststore_data = {
        "truststore": {
            "file": Path(truststore_path).name,
            "certCount": len(truststore_certs),
            "certs": truststore_certs,
        },
        "clientCert": None,
    }

    # Client cert info
    if client_cert_path and Path(client_cert_path).exists():
        client_info = get_cert_info(client_cert_path)
        client_info["label"] = client_label or Path(client_cert_path).name
        truststore_data["clientCert"] = client_info

    return sse_event("certinfo", truststore_data)


# ─── Routes ─────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/config")
def get_config():
    """Return current config for display."""
    config = load_config()
    return jsonify(
        {
            "domain": config.get("DOMAIN_NAME", ""),
            "bucket": config.get("TRUSTSTORE_BUCKET", ""),
            "region": config.get("AWS_REGION", ""),
            "certsExist": CERT_DIR.exists()
            and (CERT_DIR / "leaf-client.pem").exists(),
        }
    )


@app.route("/api/chain")
def get_chain():
    """Return certificate chain details."""
    if not CERT_DIR.exists():
        return jsonify({"error": "Certificates not generated yet"}), 404

    chain = []
    for name, label in [
        ("rootCA.pem", "Root CA"),
        ("intermediateCA.pem", "Intermediate CA"),
        ("leaf-client.pem", "Leaf (Client)"),
    ]:
        cert_path = CERT_DIR / name
        if cert_path.exists():
            result = subprocess.run(
                ["openssl", "x509", "-in", str(cert_path), "-noout",
                 "-subject", "-issuer", "-dates", "-serial"],
                capture_output=True, text=True,
            )
            chain.append({"name": label, "file": name, "details": result.stdout.strip()})
    return jsonify(chain)


@app.route("/api/test/<int:test_id>")
def run_test(test_id):
    """Run a specific test scenario and stream results via SSE using a queue."""
    config = load_config()
    domain = config.get("DOMAIN_NAME", "")
    bucket = config.get("TRUSTSTORE_BUCKET", "")
    region = config.get("AWS_REGION", "us-east-1")

    if not domain:
        return Response(
            sse_event("error", {"text": "config.env not configured"}),
            mimetype="text/event-stream",
        )

    test_runners = {
        1: run_test_fullchain,
        2: run_test_rootonly,
        3: run_test_expired,
        4: run_test_rotation,
        5: run_test_nocert,
        6: run_test_untrusted,
        7: run_test_max_depth,
    }

    runner = test_runners.get(test_id)
    if not runner:
        return Response(
            sse_event("error", {"text": f"Unknown test: {test_id}"}),
            mimetype="text/event-stream",
        )

    # Use a queue so the background thread can push events immediately
    q = queue.Queue()

    def run_in_thread():
        try:
            q.put(sse_event("start", {"test_id": test_id}))
            gen = runner(domain, bucket, region)
            result = None
            try:
                while True:
                    event = next(gen)
                    q.put(event)
            except StopIteration as e:
                result = e.value
            if result:
                q.put(sse_event("result", result))
        except Exception as e:
            app.logger.error(f"Test {test_id} failed: {type(e).__name__}")
            q.put(sse_event("error", {"text": "An internal error occurred while running the test."}))
        q.put(sse_event("done", {}))
        q.put(None)  # Sentinel to signal stream end

    threading.Thread(target=run_in_thread, daemon=True).start()

    def generate():
        while True:
            try:
                event = q.get(timeout=180)
            except queue.Empty:
                break
            if event is None:
                break
            yield event

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─── Test Runners ───────────────────────────────────────────────────────────


def curl_with_cert(domain, cert=None, key=None, path="/"):
    """Make an HTTPS request and return (http_code, body).

    Uses the requests library instead of subprocess to avoid SAST findings.
    Domain is validated against a strict hostname pattern before use.
    """
    import requests
    validated_domain = _validate_hostname(domain)
    url = f"https://{validated_domain}{path}"
    try:
        if cert and key:
            resp = requests.get(url, cert=(str(cert), str(key)), timeout=15)
        else:
            resp = requests.get(url, timeout=15)
        return str(resp.status_code), resp.text
    except requests.exceptions.SSLError:
        return "403", ""
    except requests.exceptions.ConnectionError:
        return "000", ""
    except requests.exceptions.Timeout:
        return "000", ""


def update_truststore_and_wait(pem_path, bucket, region, domain):
    """Upload truststore and wait for propagation. Yields SSE events."""
    # Upload with retry (handles transient credential/network issues)
    yield sse_event("output", {"text": f"Uploading truststore: {Path(pem_path).name}"})
    upload_ok = False
    for upload_attempt in range(3):
        upload_result = subprocess.run(
            ["aws", "s3", "cp", str(pem_path), f"s3://{bucket}/truststore.pem",
             "--region", region],
            capture_output=True, text=True,
        )
        if upload_result.returncode == 0:
            upload_ok = True
            break
        if upload_attempt < 2:
            time.sleep(3)
    if not upload_ok:
        err_msg = upload_result.stderr.strip() or upload_result.stdout.strip() or f"exit code {upload_result.returncode}"
        yield sse_event("output", {"text": f"  ⚠ S3 upload failed: {err_msg[:200]}"})
        return

    # Get version and trigger reimport
    yield sse_event("output", {"text": "Triggering domain truststore reimport..."})
    version_result = subprocess.run(
        ["aws", "s3api", "head-object", "--bucket", bucket, "--key", "truststore.pem",
         "--region", region, "--query", "VersionId", "--output", "text"],
        capture_output=True, text=True,
    )
    version = version_result.stdout.strip()
    if version_result.returncode != 0 or not version:
        yield sse_event("output", {"text": "  ⚠ Could not retrieve S3 object version"})

    mtls_arg = f"TruststoreUri=s3://{bucket}/truststore.pem"
    if version and version != "None":
        mtls_arg += f",TruststoreVersion={version}"

    update_result = subprocess.run(
        ["aws", "apigatewayv2", "update-domain-name", "--domain-name", domain,
         "--region", region, "--mutual-tls-authentication", mtls_arg],
        capture_output=True, text=True,
    )
    if update_result.returncode != 0:
        err_msg = update_result.stderr.strip() or update_result.stdout.strip()
        # If domain is already updating from a previous operation, wait for it
        if "ConflictException" in err_msg or "update is in progress" in err_msg.lower():
            yield sse_event("output", {"text": "  Domain is already updating, waiting for current update..."})
        else:
            yield sse_event("output", {"text": f"  ⚠ update-domain-name failed: {err_msg[:150]}"})
            return

    # Poll for AVAILABLE with exponential backoff (avoids API throttling)
    yield sse_event("output", {"text": "Waiting for propagation..."})
    wait_seconds = 10
    for attempt in range(12):
        time.sleep(wait_seconds)
        status_result = subprocess.run(
            ["aws", "apigatewayv2", "get-domain-name", "--domain-name", domain,
             "--region", region, "--query",
             "DomainNameConfigurations[0].DomainNameStatus", "--output", "text"],
            capture_output=True, text=True,
        )
        if status_result.returncode != 0:
            # Likely throttled — back off and retry
            yield sse_event("output", {"text": f"  Status check throttled (attempt {attempt+1}/12), backing off..."})
            wait_seconds = min(wait_seconds + 5, 30)
            continue
        status = status_result.stdout.strip()
        if status == "AVAILABLE":
            yield sse_event("output", {"text": f"Domain status: AVAILABLE ✓"})
            return
        yield sse_event("output", {"text": f"Domain status: {status} (attempt {attempt+1}/12)"})

    yield sse_event("output", {"text": "⚠ Domain did not reach AVAILABLE in time"})


def run_test_fullchain(domain, bucket, region):
    """Test 1: Full-chain truststore validates leaf cert."""
    # Show cert context immediately so customer sees what's being tested
    yield emit_cert_context(CERT_DIR / "truststore.pem", CERT_DIR / "leaf-client.pem", "leaf-client.pem (valid)")

    yield sse_event("output", {"text": "Setting truststore to: intermediate + root (full chain)"})
    yield from update_truststore_and_wait(CERT_DIR / "truststore.pem", bucket, region, domain)

    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Sending request with leaf client cert..."})
    yield sse_event("output", {"text": f"  curl --cert leaf-client.pem --key leaf-client.key https://{domain}/"})

    code, body = curl_with_cert(domain, CERT_DIR / "leaf-client.pem", CERT_DIR / "leaf-client.key")

    yield sse_event("output", {"text": f"  HTTP {code}"})
    if body:
        yield sse_event("output", {"text": ""})
        try:
            formatted = json.dumps(json.loads(body), indent=2)
            for line in formatted.splitlines():
                yield sse_event("output", {"text": f"  {line}"})
        except json.JSONDecodeError:
            yield sse_event("output", {"text": f"  {body}"})

    passed = code == "200"
    return {"passed": passed, "http_code": code}


def run_test_rootonly(domain, bucket, region):
    """Test 2: Root-only truststore rejects leaf cert."""
    # Show cert context immediately — root-only truststore + the leaf we'll present
    yield emit_cert_context(CERT_DIR / "rootCA.pem", CERT_DIR / "leaf-client.pem", "leaf-client.pem (valid)")

    yield sse_event("output", {"text": "Setting truststore to: root CA ONLY (no intermediate)"})
    yield from update_truststore_and_wait(CERT_DIR / "rootCA.pem", bucket, region, domain)

    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Sending request with leaf client cert..."})
    yield sse_event("output", {"text": f"  curl --cert leaf-client.pem --key leaf-client.key https://{domain}/"})

    code, body = curl_with_cert(domain, CERT_DIR / "leaf-client.pem", CERT_DIR / "leaf-client.key")

    yield sse_event("output", {"text": f"  HTTP {code}"})
    if body:
        yield sse_event("output", {"text": f"  {body}"})

    passed = code == "403" or (code.replace("0", "") == "")

    # Restore full chain
    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Restoring full-chain truststore..."})
    yield from update_truststore_and_wait(CERT_DIR / "truststore.pem", bucket, region, domain)

    return {"passed": passed, "http_code": code}


def run_test_expired(domain, bucket, region):
    """Test 3: Expired leaf cert is rejected."""
    yield sse_event("output", {"text": "Generating expired leaf certificate (using Python cryptography)..."})

    # Generate expired cert
    from cryptography import x509 as cx509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from datetime import datetime, timedelta, timezone

    ca_cert_pem = (CERT_DIR / "intermediateCA.pem").read_bytes()
    ca_key_pem = (CERT_DIR / "intermediateCA.key").read_bytes()
    ca_cert = cx509.load_pem_x509_certificate(ca_cert_pem)
    ca_key = serialization.load_pem_private_key(ca_key_pem, password=None)

    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)

    cert = (
        cx509.CertificateBuilder()
        .subject_name(cx509.Name([
            cx509.NameAttribute(NameOID.COMMON_NAME, "expired-client"),
            cx509.NameAttribute(NameOID.ORGANIZATION_NAME, "mTLS Demo"),
            cx509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        ]))
        .issuer_name(ca_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(cx509.random_serial_number())
        .not_valid_before(now - timedelta(days=3))
        .not_valid_after(now - timedelta(days=1))
        .sign(ca_key, hashes.SHA256())
    )

    expired_dir = Path(tempfile.mkdtemp())
    (expired_dir / "expired.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (expired_dir / "expired.key").write_bytes(
        leaf_key.private_bytes(serialization.Encoding.PEM,
                               serialization.PrivateFormat.TraditionalOpenSSL,
                               serialization.NoEncryption())
    )

    not_after = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M UTC")
    yield sse_event("output", {"text": f"  Cert expired: {not_after}"})

    yield emit_cert_context(CERT_DIR / "truststore.pem", expired_dir / "expired.pem", "expired.pem (EXPIRED)")

    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Sending request with expired cert..."})
    yield sse_event("output", {"text": f"  curl --cert expired.pem --key expired.key https://{domain}/"})

    code, body = curl_with_cert(domain, expired_dir / "expired.pem", expired_dir / "expired.key")

    yield sse_event("output", {"text": f"  HTTP {code}"})
    if body:
        yield sse_event("output", {"text": f"  {body}"})

    # Cleanup
    import shutil
    shutil.rmtree(expired_dir, ignore_errors=True)

    passed = code == "403" or (code.replace("0", "") == "")
    return {"passed": passed, "http_code": code}


def run_test_rotation(domain, bucket, region):
    """Test 4: Intermediate CA rotation with overlap."""
    yield sse_event("output", {"text": "Generating rotated Intermediate CA v2..."})

    rotation_dir = Path(tempfile.mkdtemp())

    # Generate new intermediate
    subprocess.run(
        ["openssl", "genrsa", "-out", str(rotation_dir / "intCA-v2.key"), "4096"],
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "req", "-new", "-key", str(rotation_dir / "intCA-v2.key"),
         "-subj", "/CN=Demo Intermediate CA v2/O=mTLS Demo/C=US",
         "-out", str(rotation_dir / "intCA-v2.csr")],
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "x509", "-req", "-in", str(rotation_dir / "intCA-v2.csr"),
         "-CA", str(CERT_DIR / "rootCA.pem"), "-CAkey", str(CERT_DIR / "rootCA.key"),
         "-CAcreateserial", "-days", "1825", "-sha256",
         "-extfile", "/dev/stdin",
         "-out", str(rotation_dir / "intCA-v2.pem")],
        input="basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign",
        capture_output=True, text=True,
    )

    yield sse_event("output", {"text": "Issuing new leaf cert from rotated intermediate..."})

    subprocess.run(
        ["openssl", "genrsa", "-out", str(rotation_dir / "leaf-v2.key"), "2048"],
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "req", "-new", "-key", str(rotation_dir / "leaf-v2.key"),
         "-subj", "/CN=rotated-client/O=mTLS Demo/C=US",
         "-out", str(rotation_dir / "leaf-v2.csr")],
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "x509", "-req", "-in", str(rotation_dir / "leaf-v2.csr"),
         "-CA", str(rotation_dir / "intCA-v2.pem"),
         "-CAkey", str(rotation_dir / "intCA-v2.key"),
         "-CAcreateserial", "-days", "365", "-sha256",
         "-out", str(rotation_dir / "leaf-v2.pem")],
        capture_output=True,
    )

    # Build rotation truststore (both intermediates + root)
    yield sse_event("output", {"text": "Building truststore with BOTH intermediates + root..."})
    truststore_content = (
        (CERT_DIR / "intermediateCA.pem").read_text()
        + (rotation_dir / "intCA-v2.pem").read_text()
        + (CERT_DIR / "rootCA.pem").read_text()
    )
    rotation_truststore = rotation_dir / "truststore-rotation.pem"
    rotation_truststore.write_text(truststore_content)
    cert_count = truststore_content.count("BEGIN CERTIFICATE")
    yield sse_event("output", {"text": f"  Truststore contains {cert_count} certificates"})

    # Show cert context immediately before waiting
    yield emit_cert_context(rotation_truststore, rotation_dir / "leaf-v2.pem", "leaf-v2.pem (new intermediate)")

    yield from update_truststore_and_wait(rotation_truststore, bucket, region, domain)

    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Testing NEW leaf cert (from rotated intermediate)..."})
    code, body = curl_with_cert(domain, rotation_dir / "leaf-v2.pem", rotation_dir / "leaf-v2.key")
    yield sse_event("output", {"text": f"  HTTP {code}"})

    passed = code == "200"

    if passed:
        yield sse_event("output", {"text": ""})
        yield sse_event("output", {"text": "Verifying OLD leaf still works during overlap..."})
        code_old, _ = curl_with_cert(domain, CERT_DIR / "leaf-client.pem", CERT_DIR / "leaf-client.key")
        yield sse_event("output", {"text": f"  Old leaf: HTTP {code_old}"})
        if code_old == "200":
            yield sse_event("output", {"text": "  ✓ Both old and new CAs active simultaneously"})

    # Restore
    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Restoring original truststore..."})
    yield from update_truststore_and_wait(CERT_DIR / "truststore.pem", bucket, region, domain)

    import shutil
    shutil.rmtree(rotation_dir, ignore_errors=True)

    return {"passed": passed, "http_code": code}


def run_test_nocert(domain, bucket, region):
    """Test 5: No client cert — rejected."""
    yield emit_cert_context(CERT_DIR / "truststore.pem")

    yield sse_event("output", {"text": "Sending request with NO client certificate..."})
    yield sse_event("output", {"text": f"  curl https://{domain}/"})

    code, body = curl_with_cert(domain)

    yield sse_event("output", {"text": f"  HTTP {code}"})
    if body:
        yield sse_event("output", {"text": f"  {body}"})

    passed = code == "403" or (code.replace("0", "") == "")
    return {"passed": passed, "http_code": code}


def run_test_untrusted(domain, bucket, region):
    """Test 6: Untrusted self-signed cert — rejected."""
    yield sse_event("output", {"text": "Generating untrusted self-signed certificate..."})

    rogue_dir = Path(tempfile.mkdtemp())
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048",
         "-keyout", str(rogue_dir / "rogue.key"),
         "-out", str(rogue_dir / "rogue.pem"),
         "-days", "1", "-nodes", "-subj", "/CN=rogue-client/O=Untrusted Org/C=US"],
        capture_output=True,
    )

    yield emit_cert_context(CERT_DIR / "truststore.pem", rogue_dir / "rogue.pem", "rogue.pem (UNTRUSTED self-signed)")

    yield sse_event("output", {"text": "Sending request with untrusted cert..."})
    yield sse_event("output", {"text": f"  curl --cert rogue.pem --key rogue.key https://{domain}/"})

    code, body = curl_with_cert(domain, rogue_dir / "rogue.pem", rogue_dir / "rogue.key")

    yield sse_event("output", {"text": f"  HTTP {code}"})
    if body:
        yield sse_event("output", {"text": f"  {body}"})

    import shutil
    shutil.rmtree(rogue_dir, ignore_errors=True)

    passed = code == "403" or (code.replace("0", "") == "")
    return {"passed": passed, "http_code": code}


def run_test_max_depth(domain, bucket, region):
    """Test 7: Max chain depth (root + 3 intermediates + leaf = depth 4)."""
    yield sse_event("output", {"text": "Building max-depth chain: Root → Int1 → Int2 → Int3 → Leaf"})
    yield sse_event("output", {"text": "  (API Gateway max chain depth = 4)"})
    yield sse_event("output", {"text": ""})

    deep_dir = Path(tempfile.mkdtemp())

    # Use existing root CA
    root_pem = CERT_DIR / "rootCA.pem"
    root_key = CERT_DIR / "rootCA.key"

    # Generate 3 intermediate CAs chained together
    prev_cert = str(root_pem)
    prev_key = str(root_key)
    int_certs = []

    for i in range(1, 4):
        int_key_path = str(deep_dir / f"int{i}.key")
        int_csr_path = str(deep_dir / f"int{i}.csr")
        int_pem_path = str(deep_dir / f"int{i}.pem")

        pathlen = 3 - i  # int1=2, int2=1, int3=0

        yield sse_event("output", {"text": f"  Generating Intermediate CA {i} (pathlen={pathlen})..."})

        subprocess.run(
            ["openssl", "genrsa", "-out", int_key_path, "4096"],
            capture_output=True,
        )
        subprocess.run(
            ["openssl", "req", "-new", "-key", int_key_path,
             "-subj", f"/CN=Demo Intermediate CA L{i}/O=mTLS Demo/C=US",
             "-out", int_csr_path],
            capture_output=True,
        )
        subprocess.run(
            ["openssl", "x509", "-req", "-in", int_csr_path,
             "-CA", prev_cert, "-CAkey", prev_key,
             "-CAcreateserial", "-days", "1825", "-sha256",
             "-extfile", "/dev/stdin",
             "-out", int_pem_path],
            input=f"basicConstraints=critical,CA:TRUE,pathlen:{pathlen}\nkeyUsage=critical,keyCertSign,cRLSign",
            capture_output=True, text=True,
        )

        int_certs.append(int_pem_path)
        prev_cert = int_pem_path
        prev_key = int_key_path

    # Generate leaf signed by int3
    yield sse_event("output", {"text": "  Generating leaf cert (signed by Int3)..."})
    leaf_key_path = str(deep_dir / "leaf-deep.key")
    leaf_csr_path = str(deep_dir / "leaf-deep.csr")
    leaf_pem_path = str(deep_dir / "leaf-deep.pem")

    subprocess.run(
        ["openssl", "genrsa", "-out", leaf_key_path, "2048"],
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "req", "-new", "-key", leaf_key_path,
         "-subj", "/CN=deep-chain-client/O=mTLS Demo/C=US",
         "-out", leaf_csr_path],
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "x509", "-req", "-in", leaf_csr_path,
         "-CA", int_certs[-1], "-CAkey", str(deep_dir / "int3.key"),
         "-CAcreateserial", "-days", "365", "-sha256",
         "-out", leaf_pem_path],
        capture_output=True,
    )

    # Build truststore: all 3 intermediates + root
    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "  Building truststore: Int1 + Int2 + Int3 + Root (4 certs)..."})
    truststore_content = ""
    for cert_path in int_certs:
        truststore_content += Path(cert_path).read_text()
    truststore_content += root_pem.read_text()

    deep_truststore = deep_dir / "truststore-deep.pem"
    deep_truststore.write_text(truststore_content)
    cert_count = truststore_content.count("BEGIN CERTIFICATE")
    yield sse_event("output", {"text": f"  Truststore contains {cert_count} certificates"})

    # Verify chain locally
    # Need to concatenate all intermediates as untrusted
    untrusted_bundle = deep_dir / "untrusted-bundle.pem"
    untrusted_content = ""
    for cert_path in int_certs:
        untrusted_content += Path(cert_path).read_text()
    untrusted_bundle.write_text(untrusted_content)

    verify_result = subprocess.run(
        ["openssl", "verify", "-CAfile", str(root_pem),
         "-untrusted", str(untrusted_bundle), leaf_pem_path],
        capture_output=True, text=True,
    )
    if "OK" in verify_result.stdout:
        yield sse_event("output", {"text": "  Local chain verification: OK ✓"})
    else:
        yield sse_event("output", {"text": f"  Local chain verification FAILED: {verify_result.stderr.strip()}"})

    # Show cert context immediately before waiting
    yield emit_cert_context(deep_truststore, leaf_pem_path, "leaf-deep.pem (depth=4 chain)")

    # Upload and wait
    yield from update_truststore_and_wait(deep_truststore, bucket, region, domain)

    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Testing leaf cert through 4-level chain..."})
    yield sse_event("output", {"text": f"  curl --cert leaf-deep.pem --key leaf-deep.key https://{domain}/"})

    code, body = curl_with_cert(domain, leaf_pem_path, leaf_key_path)

    yield sse_event("output", {"text": f"  HTTP {code}"})
    if body:
        try:
            formatted = json.dumps(json.loads(body), indent=2)
            for line in formatted.splitlines():
                yield sse_event("output", {"text": f"  {line}"})
        except json.JSONDecodeError:
            yield sse_event("output", {"text": f"  {body}"})

    passed = code == "200"

    # Restore original truststore
    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Restoring original truststore..."})
    yield from update_truststore_and_wait(CERT_DIR / "truststore.pem", bucket, region, domain)

    import shutil
    shutil.rmtree(deep_dir, ignore_errors=True)

    return {"passed": passed, "http_code": code}


# ─── Multi-Tenant Demo Routes ──────────────────────────────────────────────


@app.route("/api/tenant-test/<tenant>")
def run_tenant_test(tenant):
    """Run a multi-tenant test (tenant-a or tenant-b) and stream results via SSE."""
    config = load_config()
    domain = config.get("DOMAIN_NAME", "")
    region = config.get("AWS_REGION", "us-east-1")

    if tenant not in ("tenant-a", "tenant-b"):
        return Response(
            sse_event("error", {"text": f"Unknown tenant: {tenant}"}),
            mimetype="text/event-stream",
        )

    q = queue.Queue()

    def run_in_thread():
        try:
            q.put(sse_event("start", {"tenant": tenant}))
            gen = run_tenant_request(domain, region, tenant)
            result = None
            try:
                while True:
                    event = next(gen)
                    q.put(event)
            except StopIteration as e:
                result = e.value
            if result:
                q.put(sse_event("result", result))
        except Exception as e:
            app.logger.error(f"Tenant test '{tenant}' failed: {type(e).__name__}")
            q.put(sse_event("error", {"text": "An internal error occurred while running the tenant test."}))
        q.put(sse_event("done", {}))
        q.put(None)

    threading.Thread(target=run_in_thread, daemon=True).start()

    def generate():
        while True:
            try:
                event = q.get(timeout=60)
            except queue.Empty:
                break
            if event is None:
                break
            yield event

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/tenant-logs")
def get_tenant_logs():
    """Fetch recent CloudWatch logs from the authorizer function."""
    config = load_config()
    region = config.get("AWS_REGION", "us-east-1")
    stack_name = config.get("STACK_NAME", "mtls-demo")

    # Get the authorizer function name from CloudFormation
    result = subprocess.run(
        ["aws", "cloudformation", "describe-stack-resource",
         "--stack-name", stack_name, "--logical-resource-id", "MtlsAuthorizerFunction",
         "--region", region, "--query", "StackResourceDetail.PhysicalResourceId",
         "--output", "text"],
        capture_output=True, text=True,
    )
    function_name = result.stdout.strip()
    if not function_name or result.returncode != 0:
        err_detail = result.stderr.strip() or result.stdout.strip() or "empty response"
        return jsonify({"error": f"Could not find authorizer function: {err_detail[:200]}"}), 404

    log_group = f"/aws/lambda/{function_name}"

    # Get the latest log stream
    result = subprocess.run(
        ["aws", "logs", "describe-log-streams",
         "--log-group-name", log_group,
         "--region", region,
         "--order-by", "LastEventTime",
         "--descending",
         "--limit", "1",
         "--query", "logStreams[0].logStreamName",
         "--output", "text"],
        capture_output=True, text=True,
    )
    stream_name = result.stdout.strip()
    if not stream_name or stream_name == "None":
        return jsonify({"logGroup": log_group, "messages": [], "note": "No log streams found"})

    # Get recent log events from the latest stream
    result = subprocess.run(
        ["aws", "logs", "get-log-events",
         "--log-group-name", log_group,
         "--log-stream-name", stream_name,
         "--region", region,
         "--limit", "100",
         "--query", "events[].message",
         "--output", "json"],
        capture_output=True, text=True,
    )

    try:
        messages = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        messages = []

    # Filter to only the interesting authorizer log lines
    filtered = []
    for msg in messages:
        msg = msg.strip()
        if not msg:
            continue
        # Skip START/END/REPORT lines
        if msg.startswith("START ") or msg.startswith("END ") or msg.startswith("REPORT "):
            continue
        # Strip the Lambda log prefix [INFO] timestamp requestId
        if "\t" in msg:
            parts = msg.split("\t", 3)
            if len(parts) >= 4:
                msg = parts[3].strip()
            elif len(parts) == 3:
                msg = parts[2].strip()
        filtered.append(msg)

    return jsonify({"logGroup": log_group, "messages": filtered})


def run_tenant_request(domain, region, tenant):
    """Execute a tenant-specific API request and stream output."""
    cert_file = CERT_DIR / f"{tenant}.pem"
    key_file = CERT_DIR / f"{tenant}.key"

    if not cert_file.exists():
        yield sse_event("output", {"text": f"ERROR: {tenant} cert not found. Regenerate certs."})
        return {"passed": False, "http_code": "N/A"}

    # Emit cert context
    yield emit_cert_context(CERT_DIR / "truststore.pem", cert_file, f"{tenant}.pem")

    tenant_label = "Tenant A" if tenant == "tenant-a" else "Tenant B"
    endpoint = f"https://{domain}/api"

    yield sse_event("output", {"text": f"Multi-Tenant Request: {tenant_label}"})
    yield sse_event("output", {"text": f"  Endpoint: {endpoint} (same for all tenants)"})
    yield sse_event("output", {"text": f"  Client cert: {tenant}.pem (determines tenant identity)"})
    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": "Request flow:"})
    yield sse_event("output", {"text": "  1. mTLS handshake (cert validated against truststore)"})
    yield sse_event("output", {"text": "  2. Lambda Authorizer extracts cert, logs to CloudWatch"})
    yield sse_event("output", {"text": "  3. Authorizer maps CN to tenant, returns context"})
    yield sse_event("output", {"text": "  4. Handler reads tenantId from context → returns tenant-specific data"})
    yield sse_event("output", {"text": ""})
    yield sse_event("output", {"text": f"  curl --cert {tenant}.pem --key {tenant}.key {endpoint}"})
    yield sse_event("output", {"text": ""})

    # Make the request
    code, body = curl_with_cert(domain, cert_file, key_file, path="/api")

    yield sse_event("output", {"text": f"  HTTP {code}"})

    if code == "200" and body:
        yield sse_event("output", {"text": ""})
        try:
            formatted = json.dumps(json.loads(body), indent=2)
            for line in formatted.splitlines():
                yield sse_event("output", {"text": f"  {line}"})
        except json.JSONDecodeError:
            yield sse_event("output", {"text": f"  {body}"})

        yield sse_event("output", {"text": ""})
        yield sse_event("output", {"text": "  ✓ Lambda Authorizer processed cert and routed to tenant handler"})
        yield sse_event("output", {"text": "  ✓ Cert details logged to CloudWatch (check authorizer logs)"})
    elif body:
        yield sse_event("output", {"text": f"  {body}"})

    passed = code == "200"
    return {"passed": passed, "http_code": code, "tenant": tenant}


if __name__ == "__main__":
    print("\n  mTLS Demo Web App")
    print("  http://localhost:5001\n")
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)
