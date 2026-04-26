from clickhouse_driver import Client
import time
from datetime import datetime
import uuid

DATABASE = "default"
TABLE = "logs"

CH01_CONFIG = {"host": "127.0.0.1", "port": 9000}
CH02_CONFIG = {"host": "127.0.0.1", "port": 9001}
CH03_CONFIG = {"host": "127.0.0.1", "port": 9002}

KEEPER_PATH = f"/clickhouse/tables/{{shard}}/{TABLE}_{uuid.uuid4().hex}"

A_MILLION = 1_000_000

def get_client(config):
    return Client(**config)

def drop_table(client):
    client.execute(f"DROP TABLE IF EXISTS {DATABASE}.{TABLE} ON CLUSTER cluster_1S_3R")


def create_replicated_table(client):
    query = f"""
    CREATE TABLE {DATABASE}.{TABLE} ON CLUSTER cluster_1S_3R (
        timestamp DateTime,
        service_name String,
        host String,
        log_level String,
        message String
    )
    ENGINE = ReplicatedMergeTree(
        '{KEEPER_PATH}',
        '{{replica}}'
    )
    PARTITION BY toYYYYMM(timestamp)
    ORDER BY (service_name, timestamp)
    """
    client.execute(query)


def insert_logs(client, table, rows):
    query = f"""
        INSERT INTO {table} (
            timestamp,
            service_name,
            host,
            log_level,
            message
        ) VALUES
    """

    client.execute(query, rows)

def fetch_count(client):
    return client.execute(
        f"SELECT count() FROM {DATABASE}.{TABLE}"
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
    ch03 = get_client(CH03_CONFIG)
    
    drop_table(ch01)

    create_replicated_table(ch01)

    data = [
        (datetime.now(), f"auth-service-{i%10}", "host1", "INFO", f"User login success {i}")
        for i in range(0, A_MILLION)
    ]
    insert_logs(ch01, f"{DATABASE}.{TABLE}", data)
    
    if not wait_for_replication(ch02, len(data)):
        print("Replication timeout")
        return
    if not wait_for_replication(ch03, len(data)):
        print("Replication timeout")
        return

    ch1_result = fetch_count(ch01)
    ch2_result = fetch_count(ch02)
    ch3_result = fetch_count(ch03)

    if ch1_result[0][0] == ch2_result[0][0] and ch2_result[0][0] == ch3_result[0][0] and ch1_result[0][0] == A_MILLION:
        print("Replication successful")
    else:
        print("Data mismatch")
        print("Expected:", data)
        print("Got:", ch1_result, ch2_result, ch3_result)

    drop_table(ch01)

if __name__ == "__main__":
    main()