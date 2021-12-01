.PHONY: test ship
lint:
	pipenv run flake8 ./
	
test:
	pipenv run coverage run test.py
	pipenv run coverage report -m

scrape:
	pipenv run nifcwildfires active-perimeters > data/perimeters.json
	pipenv run nifcwildfires incidents > data/incidents.json

ship:
	rm -rf build/
	rm -rf dist/
	pipenv run python setup.py sdist bdist_wheel
	pipenv run twine upload dist/* --skip-existing

