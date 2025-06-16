#!/bin/bash
# Usage: ./generate_tls.sh <NODE_IP> <ROOT_CA_PASS> <CLIENT_CA_PASS> <KEYSTORE_PASS>

set -ex

NODE_IP="$1"
ROOT_CA_PASS="$2"
CLIENT_CA_PASS="$3"
KEYSTORE_PASS="$4"

if [ -z "$NODE_IP" ] || [ -z "$ROOT_CA_PASS" ] || [ -z "$CLIENT_CA_PASS" ] || [ -z "$KEYSTORE_PASS" ]; then
  echo "Usage: $0 <NODE_IP> <ROOT_CA_PASS> <CLIENT_CA_PASS> <KEYSTORE_PASS>"
  exit 1
fi


# === Check if directory already exists ===
if [ -d "$NODE_IP" ]; then
  echo "[-] Error: Directory '$NODE_IP' already exists. Please remove it or use a different IP."
  exit 1
fi

mkdir "$NODE_IP"

# === Root CA ===
if [[ -f rootCa.key && -f rootCa.crt ]]; then
  echo "[+] Root CA already exists, skipping generation."
else
  openssl req -new -x509 -newkey rsa:2048 \
    -keyout rootCa.key \
    -out rootCa.crt \
    -days 365 \
    -subj "/C=UK/O=Canonical/OU=TestCluster/CN=rootCa" \
    -passout pass:$ROOT_CA_PASS
fi

# === Setup Truststore ===
if [ -f "generic-server-truststore.jks" ]; then
  if keytool -list -keystore generic-server-truststore.jks -storepass "$KEYSTORE_PASS" -alias rootCa >/dev/null 2>&1; then
    echo "[+] Root CA already exists in truststore, skipping import."
  else
    echo "[+] Importing Root CA into truststore..."
    keytool -importcert -keystore generic-server-truststore.jks -alias rootCa \
      -file rootCa.crt -noprompt -storepass "$KEYSTORE_PASS"
  fi
else
  echo "[+] Truststore not found, creating new truststore with Root CA..."
  keytool -importcert -keystore generic-server-truststore.jks -alias rootCa \
    -file rootCa.crt -noprompt -storepass "$KEYSTORE_PASS" -keypass "$KEYSTORE_PASS"
fi

# === Client Certificate ===
echo "[+] Creating client KEY..."
openssl genrsa -out client.key 2048

echo "[+] Creating client CSR..."
openssl req -new -key client.key -out client.csr -subj "/CN=cqlsh-client"

echo "[+] Signing client CSR..."
openssl x509 -req -in client.csr -CA rootCa.crt -CAkey rootCa.key -out client.crt -days 365 -sha256 \
	-passin pass:$ROOT_CA_PASS -CAcreateserial

echo "[+] Updating server truststore..."
keytool -importcert -keystore generic-server-truststore.jks -alias client \
  -file client.crt -noprompt -storepass "$KEYSTORE_PASS"

# === Server Certificate ===
echo "[+] Generating keystore for node $NODE_IP..."
keytool -genkeypair -keyalg RSA -alias "$NODE_IP" \
  -keystore "$NODE_IP"/"$NODE_IP.jks" -storepass "$KEYSTORE_PASS" -keypass "$KEYSTORE_PASS" \
  -validity 365 -keysize 2048 \
  -dname "CN=$NODE_IP, OU=TestCluster, O=Canonical, C=UK"

echo "[+] Creating node CSR..."
keytool -certreq -keystore "$NODE_IP"/"$NODE_IP.jks" -alias "$NODE_IP" \
  -file "$NODE_IP"/"$NODE_IP.csr" -keypass "$KEYSTORE_PASS" -storepass "$KEYSTORE_PASS" \
  -dname "CN=$NODE_IP, OU=TestCluster, O=Canonical, C=UK"

echo "[+] Signing node CSR..."
openssl x509 -req -CA rootCa.crt -CAkey rootCa.key \
  -in "$NODE_IP"/"$NODE_IP.csr" -out "$NODE_IP"/"$NODE_IP.crt_signed" -days 365 \
  -CAcreateserial -passin pass:$ROOT_CA_PASS

echo "[+] Importing root CA and node cert to keystore..."
keytool -importcert -keystore "$NODE_IP"/"$NODE_IP.jks" -alias rootCa -file rootCa.crt \
  -noprompt -keypass "$KEYSTORE_PASS" -storepass "$KEYSTORE_PASS"

keytool -importcert -keystore "$NODE_IP"/"$NODE_IP.jks" -alias "$NODE_IP" -file "$NODE_IP"/"$NODE_IP.crt_signed" \
  -noprompt -keypass "$KEYSTORE_PASS" -storepass "$KEYSTORE_PASS"

# === Cleanup ===
echo "[+] Cleaning up..."
rm client.csr "$NODE_IP"/"$NODE_IP.csr"

echo "[✔] TLS certificates and truststore setup complete."
