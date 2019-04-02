""" Raw SQL for euros earned and redeemed. """
EUROS_EARNED_AND_REDEEMED_SQL = """


SELECT

	  a.owner_name												AS username
	, ROUND(IFNULL(bt.amount,0) - IFNULL(bf.amount,0),2) 		AS balance_p
	, ROUND(IFNULL(tdn.amount/100,0),2) 						AS total_donated_e
	, ROUND(IFNULL(tsp.amount/100,0),2) 						AS total_spent_e
	, ROUND(IFNULL(tsv.amount/100,0),2) 						AS total_saved_e

FROM

	accounts a  							JOIN

	members m  ON
		a.member_id = m.id				JOIN

	groups g ON
		m.group_id = g.id				LEFT JOIN

	(SELECT a.id, COUNT(t.id) AS num_trans, SUM(amount) AS amount FROM
	 `transfers` t JOIN

	 accounts a ON
		t.`from_account_id` = a.id
	  GROUP BY
		a.id) bf ON
		a.id = bf.id						LEFT JOIN

	(SELECT a.id, COUNT(t.id) AS num_trans, SUM(amount) AS amount FROM
	 `transfers` t JOIN

	 accounts a ON
		t.`to_account_id` = a.id
	  GROUP BY
		a.id) bt ON
		a.id = bt.id						LEFT JOIN

	#### TOTAL DONATED - sum of all amounts paid to charity amounts ####

	(SELECT a.id, COUNT(t.id) AS num_trans, SUM(amount) AS amount FROM
	 `transfers` t JOIN

	 `transfer_types` tt ON
		t.type_id = tt.id AND
		tt.to_account_type_id = 8 	JOIN	#goede doelen account type

	 accounts a ON
		t.`from_account_id` = a.id
	  GROUP BY
		a.id) tdn ON
		a.id = tdn.id						LEFT JOIN

	#### TOTAL SPENT - sum of all outgoing amounts to non-charity accounts ####

	(SELECT a.id, COUNT(t.id) AS num_trans, SUM(amount) AS amount FROM
	 `transfers` t JOIN

	 `transfer_types` tt ON
		t.type_id = tt.id AND
		tt.to_account_type_id <> 8 	JOIN	#other account types

	 accounts a ON
		t.`from_account_id` = a.id
	  GROUP BY
		a.id) tsp ON
		a.id = tsp.id						LEFT JOIN

	#### TOTAL SAVED - sum of all incoming amounts ####

	(SELECT a.id, COUNT(t.id) AS num_trans, SUM(amount) AS amount FROM
	 `transfers` t JOIN

	 accounts a ON
		t.`to_account_id` = a.id
	  GROUP BY
		a.id) tsv ON
		a.id = tsv.id

WHERE
	a.owner_name = %s


"""