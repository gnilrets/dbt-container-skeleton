with advances as (
  select
    advance_id,
    created_at,
    updated_at,
    provider_account_id,
    dbt_scd_id,
    dbt_valid_from,
    dbt_valid_to
  from
    {{ source('raw', 'raw_advances') }}
),

provider_accounts as (
  select
    provider_account_id,
    dbt_scd_id,
    dbt_valid_from,
    dbt_valid_to
  from
    {{ source('raw', 'raw_provider_accounts') }}
),

{{
  trange_join(
    left_model='advances',
    left_fields=['advance_id',
                'created_at',
                'updated_at',
                'provider_account_id',
                ],
    left_primary_key='advance_id',
    right_models={
      'provider_accounts': {
        'fields': [],
        'left_on': 'provider_account_id',
        'right_on': 'provider_account_id',
      }
    }
  )
}}

select * from trange_final
