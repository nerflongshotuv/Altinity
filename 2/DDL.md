CREATE TABLE {DATABASE}.{TABLE} ON CLUSTER cluster_1S_3R (
    timestamp DateTime,
    service_name String,
    host String,
    log_level String,
    message String
)
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{{shard}}/{TABLE}',
    '{{replica}}'
)
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, timestamp)