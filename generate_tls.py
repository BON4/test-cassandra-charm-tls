import os
import sys
import argparse
import subprocess


def run_cmd(cmd, **kwargs):
    print(f"[>] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def ensure_node_root_ca(node_ip, root_ca_pass):
    """Create a separate root CA for each node"""
    ca_key = os.path.join(node_ip, f"rootCa-{node_ip}.key")
    ca_crt = os.path.join(node_ip, f"rootCa-{node_ip}.crt")
    
    if os.path.isfile(ca_key) and os.path.isfile(ca_crt):
        print(f"[+] Root CA for {node_ip} already exists, skipping generation.")
        return ca_key, ca_crt
    
    print(f"[+] Creating Root CA for node {node_ip}...")
    run_cmd([
        "openssl", "req", "-new", "-x509", "-newkey", "rsa:2048",
        "-keyout", ca_key, "-out", ca_crt,
        "-days", "365",
        "-subj", f"/C=UK/O=Canonical/OU=TestCluster/CN=rootCa-{node_ip}",
        "-passout", f"pass:{root_ca_pass}"
    ])
    
    return ca_key, ca_crt


def ensure_client_root_ca(root_ca_pass):
    """Create a separate root CA for client"""
    client_dir = "client"
    ca_key = os.path.join(client_dir, "rootCa-client.key")
    ca_crt = os.path.join(client_dir, "rootCa-client.crt")
    
    if os.path.isfile(ca_key) and os.path.isfile(ca_crt):
        print("[+] Root CA for client already exists, skipping generation.")
        return ca_key, ca_crt
    
    print("[+] Creating Root CA for client...")
    run_cmd([
        "openssl", "req", "-new", "-x509", "-newkey", "rsa:2048",
        "-keyout", ca_key, "-out", ca_crt,
        "-days", "365",
        "-subj", "/C=UK/O=Canonical/OU=TestCluster/CN=rootCa-client",
        "-passout", f"pass:{root_ca_pass}"
    ])
    
    return ca_key, ca_crt


def ensure_truststore_with_client_ca(ca_crt, keystore_pass, truststore_file="generic-server-truststore.jks"):
    """Add the client's root CA to the shared truststore"""
    ca_alias = "rootCa-client"
    
    # Check if this CA is already in the truststore
    result = subprocess.run([
        "keytool", "-list", "-keystore", truststore_file,
        "-storepass", keystore_pass, "-alias", ca_alias
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if result.returncode == 0:
        print("[+] Root CA for client already in truststore, skipping import.")
        return
    
    print("[+] Importing Root CA for client into truststore...")
    run_cmd([
        "keytool", "-importcert", "-keystore", truststore_file,
        "-alias", ca_alias, "-file", ca_crt,
        "-noprompt", "-storepass", keystore_pass, "-keypass", keystore_pass
    ])
def ensure_truststore_with_node_ca(node_ip, ca_crt, keystore_pass, truststore_file="generic-server-truststore.jks"):
    """Add the node's root CA to the shared truststore"""
    ca_alias = f"rootCa-{node_ip}"
    
    # Check if this CA is already in the truststore
    result = subprocess.run([
        "keytool", "-list", "-keystore", truststore_file,
        "-storepass", keystore_pass, "-alias", ca_alias
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if result.returncode == 0:
        print(f"[+] Root CA for {node_ip} already in truststore, skipping import.")
        return
    
    print(f"[+] Importing Root CA for {node_ip} into truststore...")
    run_cmd([
        "keytool", "-importcert", "-keystore", truststore_file,
        "-alias", ca_alias, "-file", ca_crt,
        "-noprompt", "-storepass", keystore_pass, "-keypass", keystore_pass
    ])


def generate_client_cert(root_ca_pass, keystore_pass):
    """Generate client certificate using its own CA"""
    client_dir = "client"
    if not os.path.isdir(client_dir):
        os.makedirs(client_dir)
    
    # Create client's own root CA
    ca_key, ca_crt = ensure_client_root_ca(root_ca_pass)
    
    client_key = os.path.join(client_dir, "client.key")
    client_csr = os.path.join(client_dir, "client.csr")
    client_crt = os.path.join(client_dir, "client.crt")
    
    print("[+] Creating client.key...")
    run_cmd(["openssl", "genrsa", "-out", client_key, "2048"])

    print("[+] Creating client.csr...")
    run_cmd(["openssl", "req", "-new", "-key", client_key, "-out", client_csr, "-subj", "/CN=cqlsh-client"])

    print("[+] Signing client CSR with client's own CA...")
    run_cmd([
        "openssl", "x509", "-req", "-in", client_csr,
        "-CA", ca_crt, "-CAkey", ca_key,
        "-out", client_crt, "-days", "365", "-sha256",
        "-passin", f"pass:{root_ca_pass}", "-CAcreateserial"
    ])

    # Add client's CA to the shared truststore
    ensure_truststore_with_client_ca(ca_crt, keystore_pass)

    print("[+] Importing client cert into truststore...")
    run_cmd([
        "keytool", "-importcert", "-keystore", "generic-server-truststore.jks",
        "-alias", "client", "-file", client_crt,
        "-noprompt", "-storepass", keystore_pass
    ])

    os.remove(client_csr)
    print("[✔] Client certificate setup complete.")


def generate_server_cert(node_ip, root_ca_pass, keystore_pass):
    """Generate server certificate for a node using its own CA"""
    out_dir = node_ip
    if os.path.isdir(out_dir):
        print(f"[!] Directory '{out_dir}' already exists. Checking if setup is complete...")
        jks_path = os.path.join(out_dir, f"{node_ip}.jks")
        if os.path.isfile(jks_path):
            print(f"[!] Keystore for {node_ip} already exists. Skipping this node.")
            return
    else:
        os.makedirs(out_dir)

    # Create the node's own root CA
    ca_key, ca_crt = ensure_node_root_ca(node_ip, root_ca_pass)
    
    jks_path = os.path.join(out_dir, f"{node_ip}.jks")
    csr_path = os.path.join(out_dir, f"{node_ip}.csr")
    crt_signed = os.path.join(out_dir, f"{node_ip}.crt_signed")

    print(f"[+] Generating keystore for node {node_ip}...")
    run_cmd([
        "keytool", "-genkeypair", "-keyalg", "RSA", "-alias", node_ip,
        "-keystore", jks_path,
        "-storepass", keystore_pass, "-keypass", keystore_pass,
        "-validity", "365", "-keysize", "2048",
        "-dname", f"CN={node_ip}, OU=TestCluster, O=Canonical, C=UK"
    ])

    print("[+] Creating node CSR...")
    run_cmd([
        "keytool", "-certreq", "-keystore", jks_path, "-alias", node_ip,
        "-file", csr_path,
        "-keypass", keystore_pass, "-storepass", keystore_pass
    ])

    print(f"[+] Signing node CSR with node's own CA...")
    run_cmd([
        "openssl", "x509", "-req", "-CA", ca_crt, "-CAkey", ca_key,
        "-in", csr_path, "-out", crt_signed,
        "-days", "365", "-CAcreateserial", "-passin", f"pass:{root_ca_pass}"
    ])

    print(f"[+] Importing node's root CA into its keystore...")
    run_cmd([
        "keytool", "-importcert", "-keystore", jks_path,
        "-alias", f"rootCa-{node_ip}", "-file", ca_crt,
        "-noprompt", "-keypass", keystore_pass, "-storepass", keystore_pass
    ])
    
    print(f"[+] Importing signed node cert into its keystore...")
    run_cmd([
        "keytool", "-importcert", "-keystore", jks_path,
        "-alias", node_ip, "-file", crt_signed,
        "-noprompt", "-keypass", keystore_pass, "-storepass", keystore_pass
    ])

    # Add this node's CA to the shared truststore
    ensure_truststore_with_node_ca(node_ip, ca_crt, keystore_pass)

    os.remove(csr_path)
    print(f"[✔] Server certificate for {node_ip} complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate TLS certs for Cassandra nodes or clients")
    parser.add_argument("node_ips", nargs="*", help="IP addresses of Cassandra nodes (omit in client mode)")
    parser.add_argument("--client", action="store_true", help="Generate client certificate instead of server")
    parser.add_argument("--rootPass", default="myRootPass", help="Password for the Root CA key")
    parser.add_argument("--clientPass", default="myClientPass", help="Password for the Client CA key (not used)")
    parser.add_argument("--storePass", default="myKeyPass", help="Password for the Java keystore and truststore")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.client:
        generate_client_cert(args.rootPass, args.storePass)
    else:
        if not args.node_ips:
            print("[-] Error: At least one <NODE_IP> is required in server mode.")
            sys.exit(1)

        for ip in args.node_ips:
            generate_server_cert(ip, args.rootPass, args.storePass)

        print("[✔] All server certificates generated with individual CAs.")
        print("[✔] All node CAs added to shared truststore.")


if __name__ == "__main__":
    main()
