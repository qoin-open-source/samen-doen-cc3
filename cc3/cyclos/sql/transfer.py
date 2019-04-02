"""SQL for accessing Cyclos transfers directly in the Cyclos database"""

# From Simon, ticket #2577
#SELECT
#	  tf.owner_name AS sender	#this column can be removed but is just provided for human readability when testing sql
#	, uf.id AS sender_user_id
#	, tt.owner_name AS recipient	#this column can be removed but is just provided for human readability when testing sql
#	, ut.id AS recipient_user_id
#	, t.date
#	, t.process_date		#will usually be same as date, apart from transactions migrated in from old Positoos system
#	, t.amount
#	, t.type_id AS transfer_type_id
#	, t.chargeback_of_id
#	, t.description
#	, t.transaction_number
#
#FROM
#	icare4u_cyclos.transfers t 		JOIN
#
#	icare4u_cyclos.accounts tf ON
#		t.from_account_id = tf.id	JOIN
#
#	icare4u_cyclos.accounts tt ON
#		t.to_account_id = tt.id	LEFT JOIN
#
#	icare4u_front.auth_user uf ON
#		tf.owner_name = uf.username	LEFT JOIN
#
#	icare4u_front.auth_user ut ON
#		tt.owner_name = ut.username	LEFT JOIN
#
#	icare4u_front.cyclos_cc3profile pf ON
#		uf.id = pf.user_id		LEFT JOIN
#
#	icare4u_front.cyclos_cc3profile pt ON
#		ut.id = pt.user_id
#
#WHERE
#	DATE >= '2010-12-01' AND
#	DATE <= '2020-12-01' AND
#	(pf.community_id IN(1,2) OR pt.community_id IN(1,2)) AND
#	t.type_id IN (31,32,35) AND 	#cyclos transfer type id - this construct will work with just one transfer type id as well as multiples
#	(uf.id = 183 OR ut.id = 183)    #sender or recipient


TRANSFERS_SELECT = """SELECT
	  tf.owner_name AS sender	#this column can be removed but is just provided for human readability when testing sql
	, tt.owner_name AS recipient	#this column can be removed but is just provided for human readability when testing sql
	, t.date
	, t.process_date		#will usually be same as date, apart from transactions migrated in from old Positoos system
	, t.amount as amount
	, t.type_id AS transfer_type_id
	, t.chargeback_of_id
	, t.chargedback_by_id
	, t.description
	, t.transaction_number
FROM
	transfers t 		JOIN
	accounts tf ON
		t.from_account_id = tf.id	JOIN
	accounts tt ON
		t.to_account_id = tt.id
"""

TRANSFERS_TOTALS_BY_SENDER = """SELECT
	  tf.owner_name AS sender
	, SUM(t.amount) as total_amount
FROM
	transfers t 		JOIN
	accounts tf ON
		t.from_account_id = tf.id	JOIN
	accounts tt ON
		t.to_account_id = tt.id

{where_sql}

GROUP BY sender

WITH ROLLUP
"""

TRANSFERS_TOTALS_BY_RECIPIENT = """SELECT
	  tt.owner_name AS recipient
	, SUM(t.amount) as total_amount
FROM
	transfers t 		JOIN
	accounts tf ON
		t.from_account_id = tf.id	JOIN
	accounts tt ON
		t.to_account_id = tt.id

{where_sql}

GROUP BY recipient

WITH ROLLUP
"""

TRANSFERS_WHERE_SENDER = "tf.owner_name in %s"
TRANSFERS_WHERE_RECIPIENT = "tt.owner_name in %s"
TRANSFERS_WHERE_SENDER_OR_RECIPIENT = "(tf.owner_name in %s OR tt.owner_name in %s)"
TRANSFERS_WHERE_TYPE_ID = "t.type_id in %s"
TRANSFERS_WHERE_FROM_DATE = "DATE(t.date) >= %s"
TRANSFERS_WHERE_TO_DATE = "DATE(t.date) <= %s"
