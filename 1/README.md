## Replication Setup

1. Single table, replicated on entire cluster.
2. Inserted data in CH via client connected to server 1.
3. Wait for some time, then query with client connected to server 2 for the data.

## Deliverables
1. [Setup](../setup)
2. Replication successful

    ![Replcation](./images/replication_successful.png)
3. System Replicas

    ![System Replicas](./images/system_replicas.png)
4. System Parts

    ![System Parts](./images/system_parts.png)
5. Replica Server Log

    ![Replica Server Log](./images/server-02-log.png)

## References
- https://clickhouse.com/docs/engines/table-engines/mergetree-family/replication