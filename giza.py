import argparse
import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime

# URLs
UNIF_URL = "http://www.recreation.gov/unifSearchResults.do"
LOGIN_URL = "https://www.recreation.gov/memberSignInSignUp.do"
BOOKING_URL = "https://www.recreation.gov/switchBookingAction.do?"
LUBY_FULL_URL = "https://www.recreation.gov/camping/luby-bay/r/campgroundDetails.do?contractCode=NRSO&parkId=70473"

LUBY_BAY_PARK_ID = 70473

SITE_IDS = {50:1845, 52:1846, 1:1890, 18:1867, 22:1877, 24:1889, 4:1874, 5:1879, 31:1841}

def get_login_payload(email, password):
	payload = {"AemailGroup_1733152645":email,
			"ApasswrdGroup_704558654":password,
			"submitForm":"submitForm",
			"signinFromPurchaseFlow":"1",
			"sbmtCtrl":"combinedFlowSignInKit"}
	return payload

def get_site_id(site):
	return SITE_IDS[site] if site in SITE_IDS else site

# Date must be a string in the form of 7/14/2018
def get_booking_payload(site, date, length):
	payload = {"contractCode":"NRSO", 
		"parkId":LUBY_BAY_PARK_ID, 
		"lengthOfStay":length, 
		"dateChosen":"true",
		# 'site' may be either a site number (e.g. 5) or a site id (e.g. 1879).
		"siteId":get_site_id(site), 
		"arvdate":date}
	return payload

def write_html_to_file(html, filename="output.html"):
	with open(filename, "w") as file:
		file.write(str(html))

def extract_num_items_in_cart(soup_html):
	shop_cart_link_text = soup_html.find("a", {"id":"cartLink"}).text
	num_items = int(shop_cart_link_text[-1])
	print("There are {} items in the cart.".format(num_items))
	return num_items

def pretty_print_cookies(session):
	print("Cookies:")
	for key, val in session.cookies.get_dict().items():
		print("  {}: {}".format(key, val))

class GizaBot:

	def __init__(self):
		self.has_time = False
		self.hour = None
		self.minute = None
		self.second = None
		self.millisecond = None
		self.site = None
		self.date = None
		self.length = None
		self.retries = None

	def set_time(self, hour, minute, second=0, millisecond=0):
		self.has_time = True
		self.hour = hour
		self.minute = minute
		self.second = second
		self.microsecond = millisecond*1000

	def set_site(self, site):
		self.site = site

	def set_date(self, date):
		self.date = date

	def set_length_of_stay(self, length):
		self.length = length

	def set_retries(self, retries):
		self.retries = retries

	def print_info(self):
		print("Attempting to book site {} starting {} for {} days.".format(
			self.site, self.date, self.length))

	def wait(self):
		now = datetime.now()
		target_time = now.replace(hour=self.hour, minute=self.minute, second=self.second, microsecond=self.microsecond)
		time_delta = target_time-now
		time_delta_seconds = time_delta.total_seconds()
		if time_delta_seconds < 0:
			raise Exception("Wait time is negative.")
			# Wait for the bulk of the wait time using sleep()
		if time_delta_seconds > 2:
			print("Waiting {} seconds".format(time_delta_seconds))
			time.sleep(time_delta_seconds-2)
		# Busy waiting for the last 2 seconds
		now = datetime.now()
		time_delta_seconds = target_time-now
		while time_delta_seconds.total_seconds() > 0:
			now = datetime.now()
			time_delta_seconds = target_time-now

	def book_site(self, email, password):
		if self.retries < 0:
			raise ValueError("Retries must be > 0")

		self.print_info()

		with requests.Session() as s:
			login_payload = get_login_payload(email, password)
			login_response = s.post(LOGIN_URL, login_payload)
			s.get(LUBY_FULL_URL)

			booking_payload = get_booking_payload(self.site, self.date, self.length)

			if self.has_time:
				self.wait()

			# Book the site
			for i in range(self.retries):

				print("Attempted at {}".format(str(datetime.now())))
				booking_response = s.post(BOOKING_URL, booking_payload)
				
				html = BeautifulSoup(booking_response.text, 'html.parser')
				num_items = extract_num_items_in_cart(html)
				if num_items == 1:
					print("Site reserved!")
					break # don't need to retry
				else:
					print("Not reserved")

			pretty_print_cookies(s)
			write_html_to_file(html, "output_site_{}.html".format(self.site))		


if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument("-s", "--site")
	parser.add_argument("-d", "--date")
	parser.add_argument("-l", "--length", default="14")
	parser.add_argument("-r", "--retries", default="1")
	parser.add_argument("-hr", "--hour")
	parser.add_argument("-min", "--minute")
	parser.add_argument("-sec", "--second", default="0")
	parser.add_argument("-msec", "--millisecond", default="0")
	parser.add_argument("-e", "--email")
	parser.add_argument("-p", "--password")

	parser.add_argument("--jordan_default_time", choices=("0", "1", "2", "3"))

	args = parser.parse_args()
	if args.site is None or args.date is None or args.length is None or args.email is None or args.password is None:
		raise ValueError("Site, date, length, email and password must all be specified.")

	giza_bot = GizaBot()

	giza_bot.set_site(int(args.site))
	giza_bot.set_date(args.date)
	giza_bot.set_length_of_stay(args.length)
	giza_bot.set_retries(int(args.retries))

	# Default times at UTC 2:59pm to make Jordan's life easier
	default_hour = 14
	default_min = 59
	if args.jordan_default_time == "0":
		# 14:59:55:.000
		giza_bot.set_time(default_hour, default_min, 55, 0)
	elif args.jordan_default_time == "1":
		# 14:59:56.850
		giza_bot.set_time(default_hour, default_min, 56, 850)
	elif args.jordan_default_time == "2":
		# 14:59:56.900
		giza_bot.set_time(default_hour, default_min, 56, 900)
	elif args.jordan_default_time == "3":
		# 14:59:56.950
		giza_bot.set_time(default_hour, default_min, 56, 950)
	elif (args.hour is not None) and (args.minute is not None):
		hour = int(args.hour)
		minute = int(args.minute)
		second = int(args.second)
		millisecond = int(args.millisecond)
		giza_bot.set_time(hour, minute, second, millisecond)

	giza_bot.book_site(args.email, args.password)

