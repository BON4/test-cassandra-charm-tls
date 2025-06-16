# ---------- 1 ----------
# Make shure you have rootCa.key and rootCa.crt

# Output: rootCa.crt, rootCa.key

# ---------- 2 ----------
# Generate public/private key pair and keystore for each node
# Repeat this command for each node. The files can be generated on a single node (leader) and distributed out to the nodes after the entire process is completed.
# There is no convention in naming, but in this example IP adress is used
keytool -genkeypair \
    -keyalg RSA \
    -alias 10.145.156.101 \
    -keystore 10.145.156.101.jks \
    -storepass myKeyPass \
    -keypass myKeyPass \
    -validity 365 \
    -keysize 2048 \
    -dname "CN=10.145.156.101, OU=TestCluster, O=Canonical, C=UK"

# Output: 10.145.156.101.jks

# ---------- 3 ----------
# Once the node certificate and key are generated, a certificate signing request (CSR) is exported. The CSR will be signed with the rootCa certificate to verify that the node's certificate is trusted.
keytool -certreq \
    -keystore 10.145.156.101.jks \
    -alias 10.145.156.101 \
    -file 10.145.156.101.csr \
    -keypass myKeyPass \
    -storepass myKeyPass \
    -dname "CN=10.145.156.101, OU=TestCluster, O=Canonical, C=UK"

# Output: 10.145.156.101.csr

# ---------- 4 ----------
# Sign node certificate with rootCa for each node
# The CSR is input, signed with the rootCa certificate and a signed node certificate is created.
openssl x509 \
    -req \
    -CA rootCa.crt \
    -CAkey rootCa.key \
    -in 10.145.156.101.csr \
    -out 10.145.156.101.crt_signed \
    -days 365 \
    -CAcreateserial \
    -passin pass:myPass

# Output: 10.145.156.101.crt_signed

# ---------- 6 ----------
# Delete 10.145.156.101.csr
rm 10.145.156.101.csr

# ---------- 7 ----------
# Import rootCa certificate to each node keystore
# Use keytool -importcert to import the rootCa certificate into each node keystore:
keytool -importcert  \
    -keystore 10.145.156.101.jks  \
    -alias rootCa \
    -file rootCa.crt  \
    -noprompt \
    -keypass myKeyPass  \
    -storepass myKeyPass 
	
# Output: rootCa.crt added to 10.145.156.101.jks

# ---------- 8 ----------
# Import node's signed certificate into node keystore for each node
keytool -importcert \
    -keystore 10.145.156.101.jks \
    -alias 10.145.156.101  \
    -file 10.145.156.101.crt_signed \
    -noprompt \
    -keypass myKeyPass \
    -storepass myKeyPass
	
# Output: 10.145.156.101.crt_signed added to 10.145.156.101.jks	

# ---------- 9 ----------
# Create a server truststore
keytool -importcert \
    -keystore generic-server-truststore.jks \
    -alias rootCa \
    -file rootCa.crt \
    -noprompt \
    -keypass myKeyPass \
    -storepass myKeyPass
	
# Output: generic-server-truststore.jks

10.145.156.101.crt_signed
10.145.156.101.jks
generic-server-truststore.jks
rootCa.crt
rootCa.key

# Files description:
generic-server-truststore.jks - truststore is destributed across all nodes in cluster
10.145.156.101.jks - keystore is ment to be sent to the dedicated node
rootCa.crt, rootCa.key - root certificates that should be stored in secure admin palce 

# Workflow

## Add new node to the cluster
1. Node leader has rootCa.crt, rootCa.key
2. Node leader generates 10.145.156.101.jks
3. Node leader generates 10.145.156.101.csr with 10.145.156.101.jks as keystore
4. Signes 10.145.156.101.csr with rootCa and gets 10.145.156.101.crt_signed
5. 10.145.156.101.csr is deleted
6. Adds rootCa to 10.145.156.101.jks keystore
7. Adds 10.145.156.101.crt_signed to 10.145.156.101.jks keystore
8. Generate generic-server-truststore.jks truststore with rootCa
9. 10.145.156.101.jks keystore and generic-server-truststore.jks truststore is sent to the node with IP 10.145.156.101

# Cassandra setup

## cassandra-env.sh
add LOCAL_JMX=yes

## cassandra.yaml

Client:
```
client_encryption_options:
    enabled: true
    optional: false
    keystore: /var/snap/charmed-cassandra/current/etc/cassandra/ssl/10.145.156.101.jks
    keystore_password: myKeyPass
    require_client_auth: true
    truststore: /var/snap/charmed-cassandra/current/etc/cassandra/ssl/generic-server-truststore.jks
    truststore_password: myKeyPass
    cipher_suites: [TLS_RSA_WITH_AES_256_CBC_SHA]
    algorithm: SunX509
    store_type: JKS
    protocol: TLS
```

Server:
```
server_encryption_options:
    internode_encryption: all       # 'none', 'dc', or 'all'
    keystore: /var/snap/charmed-cassandra/current/etc/cassandra/ssl/10.145.156.101.jks
    keystore_password: myKeyPass
    truststore: /var/snap/charmed-cassandra/current/etc/cassandra/ssl/generic-server-truststore.jks
    truststore_password: myKeyPass
    require_client_auth: true
    cipher_suites: [TLS_RSA_WITH_AES_256_CBC_SHA]
    algorithm: SunX509
    store_type: JKS
    protocol: TLS
```

Enable cassandra 0.0.0.0 listening (if you running cassandra in vm):
```
rpc_address: 0.0.0.0
broadcast_rpc_address: 10.145.156.101
```
