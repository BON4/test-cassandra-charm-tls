
# TLS Setup for Cassandra with client_auth via truststore

## Client Certificate Generation

### Step 0 – Create `rootCa.key` and `rootCa.crt`
```bash
openssl req \
  -new -x509 \
  -newkey rsa:2048 \
  -keyout rootCa.key \
  -out rootCa.crt \
  -days 365 \
  -subj "/C=UK/O=Canonical/OU=TestCluster/CN=rootCa" \
  -passout pass:myPass
```

## Server Certificate Setup

### Step 1 – Make sure `rootCa.key` and `rootCa.crt` exist

### Step 2 – Generate keystore and key pair for each node
Repeat this command for every node (you can generate all on one node and distribute them after).
```bash
keytool -genkeypair \
    -keyalg RSA \
    -alias 10.145.156.101 \
    -keystore 10.145.156.101.jks \
    -storepass myKeyPass \
    -keypass myKeyPass \
    -validity 365 \
    -keysize 2048 \
    -dname "CN=10.145.156.101, OU=TestCluster, O=Canonical, C=UK"
```

### Step 3 – Generate CSR for the node
```bash
keytool -certreq \
    -keystore 10.145.156.101.jks \
    -alias 10.145.156.101 \
    -file 10.145.156.101.csr \
    -keypass myKeyPass \
    -storepass myKeyPass \
    -dname "CN=10.145.156.101, OU=TestCluster, O=Canonical, C=UK"
```

### Step 4 – Sign node CSR with root CA
```bash
openssl x509 \
    -req \
    -CA rootCa.crt \
    -CAkey rootCa.key \
    -in 10.145.156.101.csr \
    -out 10.145.156.101.crt_signed \
    -days 365 \
    -CAcreateserial \
    -passin pass:myPass
```

### Step 5 – Delete CSR
```bash
rm 10.145.156.101.csr
```

### Step 6 – Import root CA into node keystore
```bash
keytool -importcert \
    -keystore 10.145.156.101.jks \
    -alias rootCa \
    -file rootCa.crt \
    -noprompt \
    -keypass myKeyPass \
    -storepass myKeyPass
```

### Step 7 – Import signed certificate into node keystore
```bash
keytool -importcert \
    -keystore 10.145.156.101.jks \
    -alias 10.145.156.101 \
    -file 10.145.156.101.crt_signed \
    -noprompt \
    -keypass myKeyPass \
    -storepass myKeyPass
```

### File Descriptions
- `10.145.156.101.jks`: node-specific keystore
- `rootCa.crt`, `rootCa.key`: root CA files to be stored securely
- `client.crt`, `client.key`: client CA files

---

## Node Addition Workflow

1. Node leader has `rootCa.crt`, `rootCa.key`
2. Generates `10.145.156.101.jks`
3. Generates CSR `10.145.156.101.csr`
4. Signs it with root CA → `10.145.156.101.crt_signed`
5. Deletes CSR
6. Adds root CA to keystore
7. Adds signed cert to keystore
9. Sends `.jks` keystore to target node.

---

## Cassandra Configuration

### `cassandra-env.sh`
```bash
LOCAL_JMX=yes
```

### `cassandra.yaml`

#### Client Encryption:
```yaml
client_encryption_options:
    enabled: true
    optional: false
    keystore: /var/snap/charmed-cassandra/current/etc/cassandra/ssl/10.145.156.101.jks
    keystore_password: myKeyPass
    require_client_auth: false
    algorithm: SunX509
    store_type: JKS
    protocol: TLS
```

#### Server Encryption:
```yaml
server_encryption_options:
    internode_encryption: all
    keystore: /var/snap/charmed-cassandra/current/etc/cassandra/ssl/10.145.156.101.jks
    keystore_password: myKeyPass
    require_client_auth: false
    algorithm: SunX509
    store_type: JKS
    protocol: TLS
```

#### Enable `0.0.0.0` binding (for VMs):
```yaml
rpc_address: 0.0.0.0
broadcast_rpc_address: 10.145.156.101
```


## CQLSH configuration

### cqlshrc config:
```
[connection]
hostname = 10.145.156.101
port = 9042

[ssl]
certfile = /rootCa.crt
validate = true

```

### connect with:
```bash
cqlsh --ssl --cqlshrc=/cqlshrc
```
