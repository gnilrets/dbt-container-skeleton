with payments as (

    select * from {{ ref('stg_payments') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

final as (

    select
        orders.customer_id,
        sum(payments.amount) as total_amount

    from payments

    left join orders on payments.order_id = orders.order_id

    group by 1

)

select * from final
