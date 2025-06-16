### List of files needed to transfare to your cassandra nodes

lxc file push generic-server-truststore.jks cas-test-tls-1/tmp/
lxc file push 10.145.156.190/10.145.156.190.jks cas-test-tls-1/tmp/

lxc file push generic-server-truststore.jks cas-test-tls-2/tmp/
lxc file push 10.145.156.222/10.145.156.222.jks cas-test-tls-2/tmp/

lxc file push charmed-cassandra_5.0.4_amd64.snap cas-test-tls-1/tmp/
lxc file push charmed-cassandra_5.0.4_amd64.snap cas-test-tls-2/tmp/

lxc file push Makefile cas-test-tls-1/tmp/
lxc file push Makefile cas-test-tls-2/tmp/

lxc file push cassandra_node1.yaml cas-test-tls-1/tmp/cassandra.yaml
lxc file push cassandra_node2.yaml cas-test-tls-2/tmp/cassandra.yaml

lxc file push cassandra-env.sh cas-test-tls-1/tmp/
lxc file push cassandra-env.sh cas-test-tls-2/tmp/
