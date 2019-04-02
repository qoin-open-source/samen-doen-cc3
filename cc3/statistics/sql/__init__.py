"""
COMMON_SQL dict of SQL snippets. These can be overridden at project level,
by defining settings.STATS_CUSTOM_SQL_MODULE

If the sql snippet contains '{{community_filter}}' (EXACTLY) that will
be replaced by a suitable WHERE clause, which makes assumptions about
naming, depending on database.
for the django database:
 "community.code='xxx' AND"
for the Cyclos database:
 "cfv.string_value='{0} AND"
"""

COMMON_SQL = {

# Not (yet) implemented here:

'USERS_BY_TYPE': "",
'TOTAL_INDIVIDUAL_USERS_BY_MONTH': "",
'TOTAL_OTHER_USERS_BY_MONTH': "",

# Common queries, but can be overridden if necessary:

#################################
# TRANSACTIONS_BY_TYPE, for table
#################################
# NB. against cyclos db
# TODO: do the inactive, disabled, removed group ids need to be configurable?

'TRANSACTIONS_BY_TYPE': """SELECT
	  CONCAT(REPLACE(gf.name, ' 2',''), ' naar ', REPLACE(gt.name,' 2','')) AS `Transactie type`
	, SUM(CASE WHEN chargeback_of_id IS NULL THEN 1 ELSE 0 END) AS `Totaal aantal transacties`
	, ROUND(SUM(t.`amount`)) AS `Totale transactiewaarde`
	, ROUND(AVG(t.amount)) AS `Gemiddelde transactiewaarde`
FROM
	transfers t 				JOIN

	accounts tf ON
		t.`from_account_id` = tf.`id`	JOIN

	accounts tt ON
		t.`to_account_id` = tt.id	JOIN

       custom_field_values cfv ON
               tf.`member_id` = cfv.member_id AND
               cfv.field_id = 13               JOIN

	transfer_types txt ON
		t.`type_id` = txt.id		JOIN

	members mf ON
		tf.member_id = mf.`id`		LEFT JOIN
		
	group_history_logs ghfn ON
		mf.id = ghfn.`element_id` AND
		ghfn.end_date IS NULL AND
		mf.`group_id` IN (6,7,8)
						LEFT JOIN
		
	group_history_logs ghf ON
		ghfn.element_id = ghf.`element_id` AND
		ghf.end_date = ghfn.`start_date` AND
		ghf.`group_id` NOT IN (6,7,8)	LEFT JOIN

	groups gf ON
		gf.id = CASE WHEN mf.`group_id` IN (6,7,8) THEN ghf.group_id ELSE mf.group_id END 		JOIN

	members mt ON
		tt.member_id = mt.`id`		LEFT JOIN
		
	group_history_logs ghtn ON
		mt.id = ghtn.`element_id` AND
		ghtn.end_date > 0 AND
		mt.`group_id` IN (6,7,8)	LEFT JOIN
		
	group_history_logs ght ON
		ghtn.element_id = ght.`element_id` AND
		ght.end_date = ghtn.start_date AND
		ght.`group_id` NOT IN (6,7,8)
						LEFT JOIN

	groups gt ON
		gt.id = CASE WHEN mt.group_id IN (6,7,8) THEN ght.`group_id` ELSE mt.group_id END
		
WHERE
	t.`chargeback_of_id` IS NULL AND t.`chargedback_by_id` IS NULL AND gf.name IS NOT NULL AND gt.name IS NOT NULL AND
        {{community_filter}}  TRUE

GROUP BY
	    `Transactie type`

WITH ROLLUP
""",

##################################################
# TRANSACTION_VALUE_BY_MONTH, for discreteBarChart
##################################################
# NB. against cyclos db

'TRANSACTION_VALUE_BY_MONTH': """SELECT
	EXTRACT(YEAR_MONTH FROM DATE) AS 'x'
        , ROUND(SUM(t.`amount`)) AS `y1`
FROM
	transfers t 		JOIN

	accounts tf ON
		t.`from_account_id` = tf.`id`	JOIN

	custom_field_values cfv ON
		tf.`member_id` = cfv.member_id AND
		cfv.field_id = 13
WHERE
        {{community_filter}} TRUE

GROUP BY
	`x`
""",

##################################################
# TRANSACTION_COUNT_BY_MONTH, for discreteBarChart
##################################################
# NB. against cyclos db

'TRANSACTION_COUNT_BY_MONTH': """SELECT
	EXTRACT(YEAR_MONTH FROM DATE) AS 'x'
        , COUNT(DISTINCT t.id) AS `y1`
FROM
	transfers t 		JOIN

	accounts tf ON
		t.`from_account_id` = tf.`id`	JOIN

	custom_field_values cfv ON
		tf.`member_id` = cfv.member_id AND
		cfv.field_id = 13
WHERE
        {{community_filter}} TRUE

GROUP BY
	`x`
""",


#############################
# BALANCES_SUMMARY, for table
#############################
# NB. against cyclos db

'BALANCES_SUMMARY': """SELECT
	  REPLACE(g.name, ' 2','') AS 'Type gebruiker'
	, ROUND(SUM(cab.balance)) AS 'Gezamenlijk saldo'
	, ROUND(SUM(cab.balance)) - ROUND(SUM(clm.balance)) AS 'Toename deze maand'
	, ROUND(SUM(clm.balance)) - ROUND(SUM(ctm.balance)) AS 'Toename vorige maand'
	, ROUND(AVG(cab.balance)) AS 'Gemiddelde saldo'

FROM
	accounts a 		JOIN

	members m  ON
		a.member_id = m.id		JOIN

	groups g ON
		m.group_id = g.id		LEFT JOIN

	custom_field_values cfv ON
		m.id = cfv.member_id AND
		cfv.field_id = 13		JOIN

	(SELECT cab.account_id, cab.balance FROM closed_account_balances cab 	JOIN

	(SELECT MAX(DATE) AS DATE, account_id FROM closed_account_balances GROUP BY account_id) lb ON
		cab.`date` = lb.date AND
		cab.`account_id` = lb.account_id) cab ON

		a.id = cab.`account_id` 	LEFT JOIN

	(SELECT cab.account_id, cab.balance FROM closed_account_balances cab 	JOIN

	(SELECT MAX(DATE) AS DATE, account_id FROM closed_account_balances WHERE MONTH(DATE) < MONTH(NOW()) GROUP BY account_id) lb ON
		cab.`date` = lb.date AND
		cab.`account_id` = lb.account_id) clm ON

		a.id = clm.`account_id`		LEFT JOIN

	(SELECT cab.account_id, cab.balance FROM closed_account_balances cab 	JOIN

	(SELECT MAX(DATE) AS DATE, account_id FROM closed_account_balances WHERE DATEDIFF(NOW(),DATE) > 31 GROUP BY account_id) lb ON
		cab.`date` = lb.date AND
		cab.`account_id` = lb.account_id) ctm ON

		a.id = ctm.`account_id`

WHERE
	{{community_filter}} g.name NOT IN('Removed members','Inactive members')

GROUP BY
	`Type gebruiker`
"""
}
