from clickhouse_driver import Client
import time
from datetime import datetime
import uuid
import random
from datetime import timedelta

DATABASE = "default"
TABLE = "logs"

CH01_CONFIG = {"host": "127.0.0.1", "port": 9000}
CH02_CONFIG = {"host": "127.0.0.1", "port": 9001}
CH03_CONFIG = {"host": "127.0.0.1", "port": 9002}

KEEPER_PATH = f"/clickhouse/tables/{{shard}}/{TABLE}_{uuid.uuid4().hex}"

SERVICES = {
    "auth-service": 0.35,
    "payment-service": 0.25,
    "subscription-service": 0.15,
    "user-service": 0.15,
    "inventory-service": 0.10,
}

HOSTS = {
    "host1": 0.4,
    "host2": 0.3,
    "host3": 0.2,
    "host4": 0.1,
}

LOG_LEVEL_WEIGHTS = {
    "auth-service": {"INFO": 0.9, "WARN": 0.08, "ERROR": 0.02},
    "payment-service": {"INFO": 0.7, "WARN": 0.15, "ERROR": 0.15},
    "inventory-service": {"INFO": 0.85, "WARN": 0.1, "ERROR": 0.05},
    "default": {"INFO": 0.8, "WARN": 0.15, "ERROR": 0.05},
}

MESSAGES = {
    "INFO": [
        "Request processed",
        "User login success",
        "Cache hit",
        "Fetched data",
    ],
    "WARN": [
        "Retrying request",
        "Slow query",
        "Cache miss",
    ],
    "ERROR": [
        "DB connection failed",
        "Timeout occurred",
        "Null pointer exception",
    ],
}

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


def weighted_choice(d):
    items = list(d.items())
    values, weights = zip(*items)
    return random.choices(values, weights=weights)[0]


def generate_log(i, base_time):
    service = weighted_choice(SERVICES)

    host = weighted_choice(HOSTS)

    level_weights = LOG_LEVEL_WEIGHTS.get(service, LOG_LEVEL_WEIGHTS["default"])
    log_level = weighted_choice(level_weights)

    message = random.choice(MESSAGES[log_level])

    ts = base_time + timedelta(hours=i // 24)

    if i % 50000 < 2000:
        ts -= timedelta(hours=random.randint(0, 5))

    return (
        ts,
        service,
        host,
        log_level,
        f"{message} | req_id={i}"
    )

def insert_simulated_logs(client, table, total, batch_size=10000):
    base_time = datetime.now() - timedelta(minutes=30)

    batch = []

    for i in range(total):
        batch.append(generate_log(i, base_time))

        if len(batch) == batch_size:
            insert_logs(client, table, batch)
            batch.clear()

    if batch:
        insert_logs(client, table, batch)

def main():
    ch01 = get_client(CH01_CONFIG)
    ch02 = get_client(CH02_CONFIG)
    ch03 = get_client(CH03_CONFIG)
    
    drop_table(ch01)

    create_replicated_table(ch01)

    insert_simulated_logs(
        ch01,
        f"{DATABASE}.{TABLE}",
        total=A_MILLION
    )
    
    if not wait_for_replication(ch02, A_MILLION):
        print("Replication timeout")
        return
    if not wait_for_replication(ch03, A_MILLION):
        print("Replication timeout")
        return

    ch1_result = fetch_count(ch01)
    ch2_result = fetch_count(ch02)
    ch3_result = fetch_count(ch03)

    if ch1_result[0][0] == ch2_result[0][0] and ch2_result[0][0] == ch3_result[0][0] and ch1_result[0][0] == A_MILLION:
        print("Replication successful")
    else:
        print("Data mismatch")
        print("Expected:", A_MILLION)
        print("Got:", ch1_result, ch2_result, ch3_result)

    #drop_table(ch01)

if __name__ == "__main__":
    main()