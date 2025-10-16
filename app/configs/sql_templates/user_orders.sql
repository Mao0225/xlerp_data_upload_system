SELECT u.id AS api_user_id, u.name AS username, u.sex
FROM hruser u
{% if name is not none and name != '' %}
where name like '%{{name}}%'
{% endif %}
ORDER BY u.id
LIMIT {{limit}} OFFSET {{offset}}