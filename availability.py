import requests
from collections import defaultdict
from datetime import datetime
import json
import itertools


REQUEST_HEADERS = {"user-agent": "Chrome/71.0.3578.98",
	"origin": "https://www.recreation.gov",
	"authority":"www.recreation.gov",
	"referrer":"https://www.recreation.gov/camping/campgrounds/232199/availability",
	"content-type":"application/json;charset=UTF-8"}
JULY_URL = "https://www.recreation.gov/api/camps/availability/campground/232199/month?start_date=2019-07-01T00:00:00.000Z"
AUG_URL = "https://www.recreation.gov/api/camps/availability/campground/232199/month?start_date=2019-08-01T00:00:00.000Z"
# The format used in dates returned by recreation.gov
WEB_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# Easier to read date format.
SHORT_DATE_FORMAT = "%m/%d"
# Reference point for counting number of days since start of the year
REF_DATE = datetime(2019,1,1)

LAST_JSON = "available.json"

MIN_STAY_LENGTH = 2

def to_datetime(datestr):
	return datetime.strptime(datestr, SHORT_DATE_FORMAT)

def normalize_date(datestr):
	return datetime.strptime(datestr, WEB_DATE_FORMAT).strftime(SHORT_DATE_FORMAT)

def in_first_loop(site_number):
	return int(site_number) <= 11

def in_first_or_second_loop(site_number):
	return int(site_number) <= 24

def print_availability(d):
	print("Latest availability:")
	for k,v in sorted(d.items(), key=lambda x: x[0]):
		print("Site {} is available on {}".format(k,", ".join(v)))

def get_jsons():
	# Get latest data from recreation.gov
	july_resp = None
	aug_resp = None
	with requests.Session() as s:
		july_resp = s.get(JULY_URL, headers=REQUEST_HEADERS)
		aug_resp = s.get(AUG_URL, headers=REQUEST_HEADERS)
	return [july_resp.json(), aug_resp.json()]


def load_latest_available(jsons):
	latest_availability = defaultdict(list)
	for j in jsons:
		campsites = j["campsites"]
		for campsite in campsites.values():
			if not campsite["site"].isdigit():
				# Not a numbered site
				continue
			site_number = campsite["site"]
			if not in_first_or_second_loop(site_number):
				# Not a site we're interested in
				continue
			dates = campsite["availabilities"]
			available_dates = [normalize_date(k) for k, v in dates.items() if v=="Available"]
			if len(available_dates) > 0:
				latest_availability[site_number].extend(sorted(available_dates))
	return latest_availability

def get_new_availability(prev, latest, min_length=1):
	new_availability = {}
	for k, v in latest.items():
		if k not in prev:
			new_availability[k] = v
		else:
			new_dates = set(latest[k]).difference(set(prev[k]))
			if len(new_dates) > 0:
				new_availability[k] = new_dates
	return new_availability

def get_new_availability_interval(prev, latest, min_length=1):
	new_availability = {}
	new_dates = []
	for k, v in latest.items():
		if k not in prev:
			new_dates = get_site_new_availability([],v, min_length)
		else:
			new_dates = get_site_new_availability(prev[k], v, min_length)
		if len(new_dates) > 0:
			new_availability[k] = new_dates
	return new_availability


def get_site_new_availability(prev_dates, latest_dates, min_length):
	prev_dates_set = set(prev_dates)
	latest_dates_sorted = sorted(latest_dates)
	new_dates = []
	new_intervals = []

	grouping_func = lambda date, c=itertools.count() : (to_datetime(date) - REF_DATE).days - next(c)
	grouped_latest_dates = itertools.groupby(sorted(latest_dates), grouping_func)

	for item in grouped_latest_dates:
		dates = list(item[1])
		if len(dates) < min_length:
			continue
		if any(date not in prev_dates_set for date in dates):
			new_dates.extend(dates)
			new_intervals.append(dates)

	return new_dates #new_intervals


def load_previous(filename):
	try:
		with open(filename, 'r') as jsonfile:
			return json.load(jsonfile)
	except json.JSONDecodeError:
		print("Couldn't load json")
		return {}

def save_latest(latest, filename):
	with open(filename, 'w') as jsonfile:
		json.dump(latest, jsonfile)

if __name__ == "__main__":

	# Get the most recent data
	jsons = get_jsons()
	latest_availability = load_latest_available(jsons)
	print_availability(latest_availability)

	# Get the data from the previous run
	prev_availability = load_previous(LAST_JSON)

	new_availability = get_new_availability_interval(prev_availability, latest_availability, MIN_STAY_LENGTH)
	if not new_availability:
		print("No new availability.")
	else:
		print("New availability with {} days or more:".format(MIN_STAY_LENGTH))
		for k,v in sorted(new_availability.items(), key=lambda x: x[0]):
			print("\tSite {} on {}".format(k, ", ".join(v)))

	# Save data to compare against next time
	save_latest(latest_availability, LAST_JSON)

