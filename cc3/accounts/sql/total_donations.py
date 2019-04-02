""" Raw SQL for total donations originating with user

Calculate the total of points donated to charity for a given business's rewards
"""
TOTAL_DONATIONS_FROM_REWARDS = """
SELECT
	 CAST(SUM(d.amount) AS SIGNED)  AS donation
FROM
	accounts a 										JOIN

	transfers r ON
		a.id = r.from_account_id AND
		r.type_id = 35								JOIN

	custom_field_values cfv ON
		r.id = cfv.string_value							JOIN

	custom_fields cf ON
		cfv.`field_id` = cf.id AND
		cf.`internal_name` = 'originating_transfer_id'	JOIN

	transfers d ON
		cfv.transfer_id = d.id

WHERE
	a.owner_name = %s
"""