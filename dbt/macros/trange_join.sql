{% macro trange_join(left_model, left_fields, left_primary_key, right_models) %}
{#
  This macro allows the user to join two or more snapshot models together on a common
  key, with the result being a unique record for each distinct time range.  For example,

  Given left_model:
  | {{ join_key }} | left_field | dbt_valid_from | dbt_valid_to |
  | -              | -          | -              | -            |
  | k1             | L1         | 2020-01-01     | 2020-01-05   |
  | k1             | L2         | 2020-01-05     | 2999-12-31   |

  Given right_model:
  | {{ join_key }} | right_field | dbt_valid_from | dbt_valid_to |
  | -              | -           | -              | -            |
  | k1             | R1          | 2020-01-03     | 2020-01-07   |
  | k1             | R2          | 2020-01-07     | 2999-12-31   |


  Resultant temporal range join:
  | {{ join_key }} | left_field | right_field | dbt_valid_from | dbt_valid_to |
  | -              | -          | -           | -              | -            |
  | k1             | L1         |             | 2020-01-01     | 2020-01-03   |
  | k1             | L1         | R1          | 2020-01-03     | 2020-01-05   |
  | k1             | L2         | R1          | 2020-01-05     | 2020-01-07   |
  | k1             | L2         | R2          | 2020-01-07     | 2999-12-31   |


  Parameters:

    * left_model - Name of the "left" or primary model involved in the join.  This needs
      to be the most granular table involved in the join (the "one" in "one-to-many").
    * left_fields - An array of the fields on the left model to be included in the result.
    * left_primary_key - The primary key of the left model.  Note that this is the primary
      key of the source data, not the snapshot data (so it may not be unique in the snapshot, but
      must be unique in the source).
    * right_models - A dictionary where the keys are the names of "right" models and the values
      are another dictionary containing a list of the fields to be included in the final
      table and the join keys (see example).

  Example:
    trange_join(
      left_model='engagements',
      left_fields=engagement_fields|map('last')|list,
      left_primary_key='engagement_sfid',  # Granularit of the pre-snapshot enagement table is `engagement_sfid`
      right_models={
        'partners': {
          'fields': partner_fields|map('last')|list,
          'left_on': 'partner_sfid',
          'right_on': 'partner_sfid'
        }
      }
    )

  Requirements and assumptions:

    * Models must be CTEs, or in the default search path.
    * Models must have all of the following fields defined, and they must all be non-null:
      - dbt_scd_id
      - dbt_valid_from
      - dbt_valid_to (nulls must replaced with an open ended date like "2999-12-31 00:00:00",
        and that date must be stored in a dbt var accessible via `var('constants').OPEN_END_DATE`)
    * All other fields must not be shared between the models involved.
      Rename any shared names (other than join keys) prior to using this macro.
    * The final result is a CTE named `trange_final`.  Select from this table.


  Reference: https://www.oraylis.de/blog/combining-multiple-tables-with-valid-from-to-date-ranges-into-a-single-dimension
#}


  {%- for right_model, right_params in right_models.items() %}
    trange_unique_left_{{ right_model }} AS (
      SELECT DISTINCT
        {{ left_primary_key }},
        {{ right_params['left_on'] }} AS __left_join_key
      FROM
        {{ left_model }}
    ),

    -- The "many" side is exploded so that it ends up as a one-to-one join
    -- This prevents "ghost" rows from resulting from interactions between left records sharing in the join
    trange_explode_{{ right_model }} AS (
      SELECT
        left_model.{{ left_primary_key }},
        right_model.*
      FROM
        trange_unique_left_{{ right_model }} AS left_model
      INNER JOIN
        {{ right_model }} AS right_model
      ON
        left_model.__left_join_key = right_model.{{ right_params['right_on'] }}
    ),
  {%- endfor %}


  trange_valid_dates AS (
    SELECT {{ left_primary_key }}, dbt_valid_from AS valid_at FROM {{ left_model }}
    UNION
    SELECT {{ left_primary_key }}, dbt_valid_to AS valid_at FROM {{ left_model }}

    UNION

    {%- for right_model, _ in right_models.items() %}
      SELECT {{ left_primary_key }}, dbt_valid_from AS valid_at FROM trange_explode_{{ right_model }}
      UNION
      SELECT {{ left_primary_key }}, dbt_valid_to AS valid_at FROM trange_explode_{{ right_model }}

      {{ 'UNION' if not loop.last }}
    {%- endfor %}
  ),

  trange_all_ranges AS (
    SELECT
      {{ left_primary_key }},
      valid_at AS valid_from,
      LEAD(valid_at, 1) OVER (PARTITION BY {{ left_primary_key }} ORDER BY valid_at) AS valid_to
    FROM
      trange_valid_dates
  ),

  trange_joined_ranges AS (
    SELECT
      left_model.{{ left_primary_key }},
      left_model.dbt_scd_id AS {{ left_model }}_scd_id,

      {%- for right_model, _ in right_models.items() %}
        trange_explode_{{ right_model }}.dbt_scd_id AS {{ right_model }}_scd_id,
      {%- endfor %}

      trange_all_ranges.valid_from,
      trange_all_ranges.valid_to
    FROM
      {{ left_model }} AS left_model
    INNER JOIN
      trange_all_ranges
    ON
      left_model.{{ left_primary_key }} = trange_all_ranges.{{ left_primary_key }}
      AND left_model.dbt_valid_from < trange_all_ranges.valid_to AND left_model.dbt_valid_to > trange_all_ranges.valid_from

    {%- for right_model, right_params in right_models.items() %}
      LEFT JOIN
        trange_explode_{{ right_model }}
      ON
        left_model.{{ left_primary_key }} = trange_explode_{{ right_model }}.{{ left_primary_key }}
-- brian's line
        AND left_model.{{ right_params['left_on'] }} = trange_explode_{{ right_model }}.{{ right_params['right_on'] }}
-- end brian's line
        AND trange_explode_{{ right_model }}.dbt_valid_from < trange_all_ranges.valid_to AND trange_explode_{{ right_model }}.dbt_valid_to > trange_all_ranges.valid_from
    {%- endfor %}
  ),

  trange_final AS (
    SELECT
      {%- for left_field in left_fields %}
        left_model.{{ left_field }},
      {%- endfor %}

      {%- for right_model, right_params in right_models.items() %}
        {%- for right_field in right_params['fields'] if right_field != right_params['left_on'] %}
          {{ right_model }}.{{ right_field }},
        {%- endfor %}
      {%- endfor %}

      trange_joined_ranges.{{ left_model }}_scd_id,
      {%- for right_model, _ in right_models.items() %}
        {{ right_model }}.dbt_scd_id AS {{ right_model }}_scd_id,
      {%- endfor %}

      {{ dbt_utils.surrogate_key([
         'left_model.' ~ left_primary_key,
         'trange_joined_ranges.valid_from',
      ]) }} AS surrogate_key,
      trange_joined_ranges.valid_from,
      trange_joined_ranges.valid_to,
      trange_joined_ranges.valid_to = {{ var('constants').OPEN_END_DATE }} AS is_current
    FROM
      trange_joined_ranges
    LEFT JOIN
      {{ left_model }} AS left_model
    ON
      trange_joined_ranges.{{ left_model }}_scd_id = left_model.dbt_scd_id

    {%- for right_model, _ in right_models.items() %}
      LEFT JOIN
        {{ right_model }}
      ON
        trange_joined_ranges.{{ right_model }}_scd_id = {{ right_model }}.dbt_scd_id
    {%- endfor %}
  )


{% endmacro %}
