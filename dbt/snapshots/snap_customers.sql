{% snapshot snap_customers %}
    {{
        config(
          target_schema='snapshots',
          unique_key='id',
          strategy='check',
          check_cols=['first_name', 'last_name', 'email'],
        )
    }}

    SELECT
      *,
      CURRENT_TIMESTAMP::TIMESTAMP AS dbt_snapshot_at
    FROM
      {{ ref('raw_customers') }}
{% endsnapshot %}
