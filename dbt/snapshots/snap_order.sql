{% snapshot snap_orders %}
    {{
        config(
          target_schema='snapshots',
          unique_key='id',
          strategy='check',
          check_cols=['user_id', 'order_date', 'status'],
        )
    }}

    SELECT
        *,
        CURRENT_TIMESTAMP::TIMESTAMP AS dbt_snapshot_at
    FROM
        {{ ref('raw_orders') }}
{% endsnapshot %}
