mig:
	python manage.py makemigrations
upg:
	python manage.py migrate
super:
	python manage.py createsuperuser
apps:
	python manage.py startapp apps