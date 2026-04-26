CREATE TABLE {DATABASE}.{TABLE} ON CLUSTER cluster_1S_3R (
    id UInt32,
    value String
)
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{TABLE}',
    '{{replica}}'
)
ORDER BY id;