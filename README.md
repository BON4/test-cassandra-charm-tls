# Cassandra TLS Certificate Generator

This script generates TLS certificates for Cassandra clusters with individual Root CAs for each node and client.

## Overview

The script implements a per-node CA approach where each Cassandra node and client gets its own Root Certificate Authority. This provides better security isolation while maintaining mutual trust through a shared truststore.

## Certificate Generation Process

### For Each Node:
1. **Create Root CA** - Generate a unique Root CA for the node
2. **Create Keystore** - Generate Java keystore with node's private key
3. **Create CSR** - Generate Certificate Signing Request from keystore
4. **Sign CSR** - Sign the CSR with the node's Root CA
5. **Import to Keystore** - Import both Root CA and signed certificate to keystore
6. **Update Truststore** - Add the node's Root CA to shared truststore

*Repeat for every node in the cluster*

### For Client:
1. **Create Root CA** - Generate a unique Root CA for the client
2. **Create CSR** - Generate Certificate Signing Request
3. **Sign CSR** - Sign the CSR with client's Root CA
4. **Update Truststore** - Add client's Root CA to shared truststore
5. **Use with cqlsh** - Use the signed certificate for cqlsh connections

## Usage

### Generate Server Certificates
```bash
python generate_tls.py <node_ip1> <node_ip2> <node_ip3>
```

### Generate Client Certificates
```bash
python generate_tls.py --client
```

### Command Line Options
- `--rootPass` - Password for Root CA keys (default: myRootPass)
- `--storePass` - Password for keystores and truststore (default: myKeyPass)
- `--client` - Generate client certificate instead of server certificates

## File Structure

After running the script, you'll have:

```
.
├── generic-server-truststore.jks    # Shared truststore with all CAs
├── client/                          # Client certificates (if generated)
│   ├── rootCa-client.key
│   ├── rootCa-client.crt
│   ├── client.key
│   └── client.crt
├── <node_ip1>/                      # Node-specific certificates
│   ├── rootCa-<node_ip1>.key
│   ├── rootCa-<node_ip1>.crt
│   ├── <node_ip1>.jks               # Node's keystore
│   └── <node_ip1>.crt_signed
└── <node_ip2>/
    ├── rootCa-<node_ip2>.key
    ├── rootCa-<node_ip2>.crt
    ├── <node_ip2>.jks
    └── <node_ip2>.crt_signed
```

## Cassandra Configuration

### Server Configuration
1. Copy the node's `.jks` file to the Cassandra node
2. Copy the `generic-server-truststore.jks` to all nodes
3. Update `cassandra.yaml` with SSL settings (use [cassandra_node1.yaml](https://github.com/BON4/test-cassandra-charm-tls/blob/main/cassandra_node1.yaml) and [cassandra_node2.yaml](https://github.com/BON4/test-cassandra-charm-tls/blob/main/cassandra_node2.yaml) in this codebase for reference):
   - Point to the node's keystore
   - Point to the shared truststore
   - Configure SSL ports and encryption
4. Update `cassandra-env.sh` (use [cassandra-env.sh](https://github.com/BON4/test-cassandra-charm-tls/blob/main/cassandra-env.sh) in this codebase for reference)

### Client Configuration
1. Update `cqlshrc` configuration file with:
   - Path to client certificate
   - Path to client key
   - Cassandra node IP address

### Connecting with cqlsh
```bash
cqlsh --ssl --cqlshrc=/path/to/cqlshrc
```

## Important Notes

- Each node has its own Root CA for maximum security isolation
- The shared truststore contains all Root CAs for mutual authentication
- IP addresses in configuration files must match your actual node IPs
- Always update the truststore on existing nodes when adding new nodes or clients
- Keep Root CA private keys secure and backed up

## Security Benefits

- **Isolation**: Each node/client has its own CA, limiting blast radius
- **Mutual Trust**: Shared truststore enables cluster-wide authentication
- **Flexibility**: Easy to revoke or replace certificates for individual nodes
- **Compliance**: Meets enterprise security requirements for certificate management
