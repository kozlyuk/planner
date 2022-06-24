#!/bin/sh

if [ "$DATABASE" = "mysql" ]
then
    echo "Connectiong to DB $DB_HOST $DB_PORT ..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done

    echo "MySQL started"
fi

python manage.py migrate
echo "Migrating completed"
python manage.py collectstatic --no-input
echo "Collecting staticfiles completed"

exec "$@"
