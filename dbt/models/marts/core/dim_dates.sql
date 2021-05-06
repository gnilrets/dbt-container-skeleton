WITH spine AS (
{{ dbt_utils.date_spine(
      datepart="day",
      start_date="to_date('2020-01-01', 'yyyy-mm-dd')",
      end_date="to_date('2021-01-01', 'yyyy-mm-dd')"
     )
  }}
)

SELECT
    date_day::DATE AS date_day,
    date_part('MONTH', date_day) AS date_month,
    date_part('YEAR', date_day) AS date_year
FROM
    spine