export_invoices_sql = """USE {{DJANGO_DB_NAME}};

SET @invdate = DATE_FORMAT(DATE({{INVOICE_DATE}}),'%Y%m01');
SET @m = 1;

SELECT
	  'Factuurtype'
	, 'Debiteur'
	, 'Nummer'
	, 'Factuurdatum'
	, 'Vervaldatum'
	, 'Kop'
	, 'Voet'
	, 'Valuta'
	,  'Aantal'
	, 'Artikel'
	, 'Subartikel'
	, 'Omschrijving'
	, 'Artikel prijs(excl btw)'
	, 'Artikel prijs(incl btw)'
	, 'BTW'
	, 'Grootboekrek'
	, 'Vrij tekstveld 1'
	, 'Vrij tekstveld 2'
	, 'Vrij tekstveld 3'

UNION

SELECT
	  '01'																				AS Factuurtype	#, u.email, u.username
	, CONCAT('SD',LEFT('000000',6-LENGTH(u.id)),u.id) 									AS Debiteur
	, CONCAT(@invdate,LEFT('000000',6-LENGTH(u.id)),u.id)	AS Nummer
	, DATE_FORMAT(@invdate, '%d-%m-%Y')												AS Factuurdatum
	, ''																					AS Vervaldatum
	, CONCAT('Maandelijkse afrekening  Samen doen punten ',
		DATE_FORMAT(DATE_SUB(@invdate,INTERVAL @m MONTH),'01-%m-%Y')
		, ' tot ', DATE_FORMAT(@invdate, '01-%m-%Y')) 									AS Kop
	, ''																					AS Voet
	, 'EUR'																				AS Valuta
	, CAST(IFNULL(bf.amount,0) AS SIGNED)												AS Aantal
	, 1001																				AS Artikel
	, 101																				AS Subartikel
	, ''																					AS Omschrijving
	, 0.01																				AS `Artikel prijs(excl btw)`
	, ''																					AS `Artikel prijs(incl btw)`
	, 'VV'																				AS BTW
	, ''																					AS Grootboekrek
	, 'P0001'																			AS `Vrij tekstveld 1`
	, CONCAT('Periode '
		, DATE_FORMAT(DATE_SUB(@invdate,INTERVAL @m MONTH),'01-%m-%Y')
		, ' tot ', DATE_FORMAT(@invdate, '01-%m-%Y'))										AS `Vrij tekstveld 2`
	, ''																					AS `Vrij tekstveld 3`

FROM
	auth_user u 							JOIN

	cyclos_cc3profile p ON
		u.id = p.user_id					JOIN

	cyclos_cyclosaccount ca ON
		p.id = ca.cc3_profile_id			JOIN

	{{CYCLOS_DB_NAME}}.accounts a ON
		a.`owner_name` = u.username	JOIN

	{{CYCLOS_DB_NAME}}.members m  ON
		a.member_id = m.id				JOIN

	{{CYCLOS_DB_NAME}}.groups g ON
		m.group_id = g.id				LEFT JOIN

	(SELECT a.id, COUNT(t.id) AS num_trans, SUM(amount) AS amount FROM
	 {{CYCLOS_DB_NAME}}.`transfers` t 			JOIN

	 {{CYCLOS_DB_NAME}}.accounts a ON
		t.`from_account_id` = a.id
	 WHERE
		t.date < @invdate AND
		t.date >= DATE_SUB(@invdate,INTERVAL @m MONTH) AND
		t.`description` NOT LIKE '% automatisch incasso'
	  GROUP BY
		a.id) bf ON
		a.id = bf.id

WHERE
	u.is_active = 1 AND
	g.id = 12 AND
	bf.amount > 0

UNION


SELECT
	  '01'																				AS Factuurtype		#, u.email, u.username
	, CONCAT('SD',LEFT('000000',6-LENGTH(u.id)),u.id) 									AS Debiteur
	, CONCAT(@invdate,LEFT('000000',6-LENGTH(u.id)),u.id)	AS Nummer
	, DATE_FORMAT(@invdate, '%d-%m-%Y')												AS Factuurdatum
	, ''																					AS Vervaldatum
	, CONCAT('Maandelijkse afrekening  Samen doen punten ',
		DATE_FORMAT(DATE_SUB(@invdate,INTERVAL @m MONTH),'01-%m-%Y')
		, ' tot ', DATE_FORMAT(@invdate, '01-%m-%Y')) 										AS Kop
	, ''																					AS Voet
	, 'EUR'																				AS Valuta
	, CAST(IFNULL(-bt.amount,0) AS SIGNED)												AS Aantal
	, 1001																				AS Artikel
	, 102																				AS Subartikel
	, ''																					AS Omschrijving
	, 0.01																				AS `Artikel prijs(excl btw)`
	, ''																					AS `Artikel prijs(incl btw)`
	, 'VV'																				AS BTW
	, ''																					AS Grootboekrek
	, 'P0001'																			AS `Vrij tekstveld 1`
	, CONCAT('Periode '
		, DATE_FORMAT(DATE_SUB(@invdate,INTERVAL @m MONTH),'01-%m-%Y')
		, ' tot ', DATE_FORMAT(@invdate, '01-%m-%Y'))										AS `Vrij tekstveld 2`
	, ''																					AS `Vrij tekstveld 3`

FROM
	auth_user u 				JOIN

	cyclos_cc3profile p ON
		u.id = p.user_id		JOIN

	cyclos_cyclosaccount ca ON
		p.id = ca.cc3_profile_id	JOIN

	{{CYCLOS_DB_NAME}}.accounts a ON
		a.`owner_name` = u.username	JOIN

	{{CYCLOS_DB_NAME}}.members m  ON
		a.member_id = m.id		JOIN

	{{CYCLOS_DB_NAME}}.groups g ON
		m.group_id = g.id		LEFT JOIN

	(SELECT a.id, COUNT(t.id) AS num_trans, SUM(amount) AS amount FROM
	 {{CYCLOS_DB_NAME}}.`transfers` t JOIN

	 {{CYCLOS_DB_NAME}}.accounts a ON
		t.`to_account_id` = a.id
	 WHERE
		t.date < @invdate AND
		t.date >= DATE_SUB(@invdate,INTERVAL @m MONTH) AND
		t.`description` NOT LIKE '% automatisch incasso'
	  GROUP BY
		a.id) bt ON
		a.id = bt.id

WHERE
	u.is_active = 1 AND
	g.id = 12 AND
	bt.amount > 0

ORDER BY
	Debiteur

INTO OUTFILE '{{OUTPUT_FILE}}'
FIELDS TERMINATED BY ';'
LINES TERMINATED BY '\\n'
;
"""