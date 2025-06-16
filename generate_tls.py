import os
import sys
import argparse
import subprocess


def run_cmd(cmd, **kwargs):
    print(f"[>] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def ensure_root_ca(root_ca_pass):
    if os.path.isfile("rootCa.key") and os.path.isfile("rootCa.crt"):
        print("[+] Root CA already exists, skipping generation.")
    else:
        run_cmd([
            "openssl", "req", "-new", "-x509", "-newkey", "rsa:2048",
            "-keyout", "rootCa.key", "-out", "rootCa.crt",
            "-days", "365",
            "-subj", "/C=UK/O=Canonical/OU=TestCluster/CN=rootCa",
            "-passout", f"pass:{root_ca_pass}"
        ])


def ensure_truststore_with_root_ca(keystore_pass, truststore_file="generic-server-truststore.jks"):
    if os.path.isfile(truststore_file):
        result = subprocess.run([
            "keytool", "-list", "-keystore", truststore_file,
            "-storepass", keystore_pass, "-alias", "rootCa"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            print("[+] Root CA already in truststore, skipping import.")
            return
    print("[+] Importing Root CA into truststore...")
    run_cmd([
        "keytool", "-importcert", "-keystore", truststore_file,
        "-alias", "rootCa", "-file", "rootCa.crt",
        "-noprompt", "-storepass", keystore_pass, "-keypass", keystore_pass
    ])


def generate_client_cert(root_ca_pass, keystore_pass):
    print("[+] Creating client.key...")
    run_cmd(["openssl", "genrsa", "-out", "client.key", "2048"])

    print("[+] Creating client.csr...")
    run_cmd(["openssl", "req", "-new", "-key", "client.key", "-out", "client.csr", "-subj", "/CN=cqlsh-client"])

    print("[+] Signing client CSR...")
    run_cmd([
        "openssl", "x509", "-req", "-in", "client.csr",
        "-CA", "rootCa.crt", "-CAkey", "rootCa.key",
        "-out", "client.crt", "-days", "365", "-sha256",
        "-passin", f"pass:{root_ca_pass}", "-CAcreateserial"
    ])

    print("[+] Importing client cert into truststore...")
    run_cmd([
        "keytool", "-importcert", "-keystore", "generic-server-truststore.jks",
        "-alias", "client", "-file", "client.crt",
        "-noprompt", "-storepass", keystore_pass
    ])

    os.remove("client.csr")
    print("[✔] Client certificate setup complete.")


def generate_server_cert(node_ip, root_ca_pass, keystore_pass):
    out_dir = node_ip
    if os.path.isdir(out_dir):
        print(f"[!] Directory '{out_dir}' already exists. Skipping this node.")
        return

    os.makedirs(out_dir)
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

    print("[+] Signing node CSR...")
    run_cmd([
        "openssl", "x509", "-req", "-CA", "rootCa.crt", "-CAkey", "rootCa.key",
        "-in", csr_path, "-out", crt_signed,
        "-days", "365", "-CAcreateserial", "-passin", f"pass:{root_ca_pass}"
    ])

    print("[+] Importing root CA and node cert into keystore...")
    run_cmd([
        "keytool", "-importcert", "-keystore", jks_path,
        "-alias", "rootCa", "-file", "rootCa.crt",
        "-noprompt", "-keypass", keystore_pass, "-storepass", keystore_pass
    ])
    run_cmd([
        "keytool", "-importcert", "-keystore", jks_path,
        "-alias", node_ip, "-file", crt_signed,
        "-noprompt", "-keypass", keystore_pass, "-storepass", keystore_pass
    ])

    os.remove(csr_path)
    print(f"[✔] Server certificate for {node_ip} complete.")


def import_node_cert_into_truststore(node_ip, keystore_pass, truststore_file="generic-server-truststore.jks"):
    jks_path = os.path.join(node_ip, f"{node_ip}.jks")
    exported_cert_path = os.path.join(node_ip, f"{node_ip}.crt")

    if not os.path.isfile(jks_path):
        print(f"[!] Keystore not found for {node_ip}, skipping.")
        return

    print(f"[+] Exporting certificate for {node_ip} from keystore...")
    run_cmd([
        "keytool", "-export",
        "-alias", node_ip,
        "-file", exported_cert_path,
        "-keystore", jks_path,
        "-storepass", keystore_pass,
        "-rfc"
    ])

    print(f"[+] Importing exported cert into truststore as alias '{node_ip}'...")
    run_cmd([
        "keytool", "-importcert",
        "-keystore", truststore_file,
        "-alias", node_ip,
        "-file", exported_cert_path,
        "-noprompt",
        "-storepass", keystore_pass
    ])


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

    ensure_root_ca(args.rootPass)
    ensure_truststore_with_root_ca(args.storePass)

    if args.client:
        generate_client_cert(args.rootPass, args.storePass)
    else:
        if not args.node_ips:
            print("[-] Error: At least one <NODE_IP> is required in server mode.")
            sys.exit(1)

        for ip in args.node_ips:
            generate_server_cert(ip, args.rootPass, args.storePass)

        print("[+] Adding all node certs from keystores to truststore...")
        for node_ip in args.node_ips:
            import_node_cert_into_truststore(node_ip, args.storePass)

        print("[✔] All server certs added to truststore.")


if __name__ == "__main__":
    main()
