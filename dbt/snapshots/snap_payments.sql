{% snapshot snap_payments %}
    {{
        config(
          target_schema='snapshots',
          unique_key='id',
          strategy='check',
          check_cols=['order_id', 'payment_method', 'amount'],
        )
    }}

    SELECT
      *,
      CURRENT_TIMESTAMP::TIMESTAMP AS dbt_snapshot_at
    FROM
      {{ ref('raw_payments') }}
{% endsnapshot %}
