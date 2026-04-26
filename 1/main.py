from clickhouse_driver import Client
import time
import uuid

DATABASE = "default"
TABLE = f"replicated_test_{uuid.uuid4().hex}"

CH01_CONFIG = {"host": "127.0.0.1", "port": 9000}
CH02_CONFIG = {"host": "127.0.0.1", "port": 9001}


def get_client(config):
    return Client(**config)


def drop_table(client):
    client.execute(f"DROP TABLE IF EXISTS {DATABASE}.{TABLE} ON CLUSTER cluster_1S_3R")


def create_replicated_table(client):
    query = f"""
    CREATE TABLE {DATABASE}.{TABLE} ON CLUSTER cluster_1S_3R (
        id UInt32,
        value String
    )
    ENGINE = ReplicatedMergeTree(
        '/clickhouse/tables/{TABLE}',
        '{{replica}}'
    )
    ORDER BY id
    """
    client.execute(query)


def insert_data(client, data):
    client.execute(
        f"INSERT INTO {DATABASE}.{TABLE} (id, value) VALUES",
        data
    )


def fetch_all(client):
    return client.execute(
        f"SELECT id, value FROM {DATABASE}.{TABLE} ORDER BY id"
    )


def wait_for_replication(client, expected_count, timeout=10):
    for _ in range(timeout):
        count = client.execute(
            f"SELECT count() FROM {DATABASE}.{TABLE}"
        )[0][0]

        if count == expected_count:
            return True

        time.sleep(1)

    return False


def main():
    ch01 = get_client(CH01_CONFIG)
    ch02 = get_client(CH02_CONFIG)

    drop_table(ch01)

    create_replicated_table(ch01)

    data = [(1, "a"), (2, "b"), (3, "c")]
    insert_data(ch01, data)
    
    if not wait_for_replication(ch02, len(data)):
        print("Replication timeout")
        return

    result = fetch_all(ch02)

    if result == data:
        print("Replication successful")
    else:
        print("Data mismatch")
        print("Expected:", data)
        print("Got:", result)

    drop_table(ch01)

if __name__ == "__main__":
    main()