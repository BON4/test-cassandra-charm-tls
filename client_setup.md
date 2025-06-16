# Создание клиентских сертификатов для Cassandra TLS

### 0. Создать rootCa.key и rootCa.crt
```
openssl req \
  -new -x509 \
  -newkey rsa:2048 \
  -keyout rootCa.key \
  -out rootCa.crt \
  -days 365 \
  -subj "/C=UK/O=Canonical/OU=TestCluster/CN=rootCa" \
  -passout pass:myPass
```

### 1. Создать клиентский keystore
```bash
keytool -genkeypair \
    -keyalg RSA \
    -alias client \
    -keystore client.jks \
    -storepass myKeyPass \
    -keypass myKeyPass \
    -validity 365 \
    -keysize 2048 \
    -dname "CN=client, OU=TestCluster, O=Canonical, C=UK"
```

### 2. Создать CSR для клиента
```bash
keytool -certreq \
    -keystore client.jks \
    -alias client \
    -file client.csr \
    -keypass myKeyPass \
    -storepass myKeyPass
```

### 3. Подписать клиентский CSR корневым CA
```bash
openssl x509 \
    -req \
    -CA rootCa.crt \
    -CAkey rootCa.key \
    -in client.csr \
    -out client.crt_signed \
    -days 365 \
    -CAcreateserial \
    -passin pass:myPass
```

### 4. Импортировать корневой сертификат в клиентский keystore
```bash
keytool -importcert \
    -keystore client.jks \
    -alias rootCa \
    -file rootCa.crt \
    -noprompt \
    -keypass myKeyPass \
    -storepass myKeyPass
```

### 5. Импортировать подписанный клиентский сертификат
```bash
keytool -importcert \
    -keystore client.jks \
    -alias client \
    -file client.crt_signed \
    -noprompt \
    -keypass myKeyPass \
    -storepass myKeyPass
```

### 6. Конвертировать JKS в PKCS12
```bash
keytool -importkeystore \
    -srckeystore client.jks \
    -destkeystore client.p12 \
    -deststoretype PKCS12 \
    -srcstorepass myKeyPass \
    -deststorepass myKeyPass
```

### 7. Извлечь приватный ключ и сертификат в PEM формат
```bash
# Извлечь приватный ключ без пароля
openssl pkcs12 -in client.p12 \
    -nocerts -out client.key \
    -passin pass:myKeyPass \
    -nodes

# Извлечь клиентский сертификат
openssl pkcs12 -in client.p12 \
    -nokeys -out client.crt \
    -passin pass:myKeyPass
```

### 8. Добавить клиентский сертификат в server truststore
```bash
keytool -importcert \
    -keystore generic-server-truststore.jks \
    -alias client \
    -file client.crt \
    -noprompt \
    -storepass myKeyPass
```

### 9. Очистить временные файлы
```bash
rm client.csr client.crt_signed client.p12 client.jks
```
