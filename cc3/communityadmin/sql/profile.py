""" Raw SQL for community admin members list. """
COMMUNITY_MEMBER_LIST = """
SELECT
      `profile`.`id`
    , `profile`.`first_name`
    , `profile`.`last_name`
    , `profile`.`job_title`
    , `user`.`username` AS member_username
    , `user`.`email` AS member_email
    , `profile`.`business_name`
    , `profile`.`company_website`
    , COALESCE( offers.cnt, 0 ) AS count_offers
    , COALESCE( wants.cnt, 0 ) AS count_wants
    , FALSE AS has_full_account
    , COALESCE( active.cnt, 0) AS count_active_ads
    , `user`.`date_joined` AS date_joined
 FROM `cyclos_cc3profile` AS profile
   LEFT JOIN
      ( SELECT created_by_id, COUNT(*) AS cnt
      FROM marketplace_ad
      WHERE marketplace_ad.`adtype_id` = 1
      GROUP BY created_by_id ) offers
     ON `profile`.`id` = offers.created_by_id
   LEFT JOIN
      ( SELECT created_by_id, COUNT(*) AS cnt
      FROM marketplace_ad
      WHERE marketplace_ad.`adtype_id` = 2
      GROUP BY created_by_id ) wants
     ON `profile`.`id` = wants.created_by_id
   LEFT JOIN
      ( SELECT created_by_id, COUNT(*) AS cnt
      FROM marketplace_ad
      WHERE marketplace_ad.`status` = 'active'
      GROUP BY created_by_id ) active
     ON `profile`.`id` = active.created_by_id
    LEFT JOIN
        auth_user AS `user`
        ON `profile`.`user_id` = `user`.id

    WHERE `profile`.`community_id` = %s
"""

COMMUNITY_MEMBER_LIST_WHERE_EXTRA = """
      AND (
        `profile`.`first_name` LIKE %s OR
        `profile`.`last_name` LIKE %s OR
        `profile`.`business_name` LIKE %s OR
        `user`.`email` LIKE %s
      )
"""
