# vaptac-technology/vatpac-routes
Attatched is complete list of all preffered or required routes in Australian Airspace. 
Will be kept up to date inline with Airservices 3 monthly DAP Updates (Airac )

### Use Case
This repository is presently utilised to update Simbrief routes for which pilots utilise when generating a new flight plan.

## find_lowercase_route_lines.py
This is super handy to find the anoying airservices notes that should not be in the middle of a route. Just run `python find_lowercase_route_lines.py` in the integrated terminal.

## validate_routes_against_airspace.py
This script validates the routes in latest_routes.json against Airspace.xml from the vatSys australia-dataset repository.

Usage:
- `python validate_routes_against_airspace.py`
- `python validate_routes_against_airspace.py --branch 2509draft`
- `python validate_routes_against_airspace.py --branch 2511draft --routes-file latest_routes.json`

The script will prompt you for a branch name if you do not pass one, download Airspace.xml for that branch, and report route tokens that are not present in the dataset.