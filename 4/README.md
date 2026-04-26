# 
1. Verifying initial data accross replicas
    - ![Count per replica](./images/count_per_replica.png)
2. Stopping server 2
    - ![Stop server 2](./images/docker_stop.png)
3. Inserting data while server 2 is down
    - Inserting random seed data, which creates many parts
    ```sql
    INSERT INTO logs
    SELECT
        now(),
        'auth-service',
        concat('host', toString(rand()%10)),
        'INFO',
        toString(rand())
    FROM numbers(100_000_000);
    ```
    - ![Insert 5000000 rows](./images/insert_5000000_rows.png)
    - ![Server fail logs](./images/server_fail_logs.png)
    - ![Active replicas](./images/active_replicas.png)
    - Altering tables for mutations
    ```sql
    ALTER TABLE logs
    UPDATE log_level = 'ERROR'
    WHERE service_name = 'auth-service';

    ALTER TABLE logs
    DELETE WHERE log_level = 'WARN';

    ALTER TABLE logs
    UPDATE message = 'fixed message'
    WHERE log_level = 'ERROR';
    ```
4. Bringing back server 2
    -  ![back server 2](./images/back_server_02.png)
    -  Checking replication queue
        ![queue](./images/queue.png)
    - Checking replicas
        ![replicas](./images/replica.png)
    - Checking mutations
        ![mutations](./image/alter_mutations.png)
    - Post mutation complete
        ![mutations](./images/mutations_done.png)
5. Checking consistency post operations
    - Server 1
        ![server 1](./images/final_1.png)
    - Server 2
        ![server 2](./images/final_2.png)
    - Server 3
        ![server 3](./images/final_3.png)