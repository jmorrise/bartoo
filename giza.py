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
LENGTH_OF_STAY = 1
ARRIVAL_DATE = "6/17/2018"

SITE_IDS = {50:1845, 1:1890, 18:1867, 22:1877, 24:1889}

def get_login_payload(email, password):
	payload = {"AemailGroup_1733152645":email,
			"ApasswrdGroup_704558654":password,
			"submitForm":"submitForm",
			"signinFromPurchaseFlow":"1",
			"sbmtCtrl":"combinedFlowSignInKit"}
	return payload

# Date must be a string in the form of 7/14/2018
def get_booking_payload(site, date, length):
	payload = {"contractCode":"NRSO", 
		"parkId":LUBY_BAY_PARK_ID, 
		"lengthOfStay":length, 
		"dateChosen":"true",
		"siteId":SITE_IDS[site], 
		"arvdate":date}
	return payload

def write_response_html_to_file(response, filename="output.html"):
	html = BeautifulSoup(response.text, 'html.parser')

	with open(filename, "w") as file:
		file.write(str(html))

def extract_num_items_in_cart(soup_html):
	shop_cart_link_text = soup_html.find("a", {"id":"cartLink"}).text
	print("'{}' is the shopping cart link text.".format(shop_cart_link_text))
	num_items = int(shop_cart_link_text[-1])
	print("There are {} items in the cart.".format(num_items))
	return num_items

class GizaBot:

	def __init__(self):
		self.has_time = False
		self.hour = None
		self.minute = None
		self.second = None
		self.site = None
		self.date = None
		self.length = None
		self.retries = None

	def set_time(self, hour, minute, second=0):
		self.has_time = True
		self.hour = hour
		self.minute = minute
		self.second = second

	def set_site(self, site):
		self.site = site

	def set_date(self, date):
		self.date = date

	def set_length_of_stay(self, length):
		self.length = length

	def set_retries(self, retries):
		self.retries = retries

	def wait(self):
		now = datetime.now()
		target_time = now.replace(hour=self.hour, minute=self.minute, second=self.second, microsecond=0)
		time_delta = target_time-now
		time_delta_seconds = time_delta.total_seconds()
		if time_delta_seconds < 0:
			raise Exception("Wait time is negative.")
		if time_delta_seconds > 2:
			print("Waiting {} seconds".format(time_delta_seconds))
			time.sleep(time_delta_seconds-2)
		now = datetime.now()
		while (now.hour != self.hour) or (now.minute != self.minute) or (now.second != self.second):
			time.sleep(0)
			now = datetime.now()

	def book_site(self, email, password):
		if self.retries < 0:
			raise ValueError("Retries must be > 0")

		with requests.Session() as s:
			login_payload = get_login_payload(email, password)
			login_response = s.post(LOGIN_URL, login_payload)
			s.get(LUBY_FULL_URL)

			booking_payload = get_booking_payload(self.site, self.date, self.length)
			print(booking_payload)

			if self.has_time:
				self.wait()

			# Book the site
			for i in range(self.retries):

				booking_response = s.post(BOOKING_URL, booking_payload)

				print("attempted at {}".format(str(datetime.now())))
				if (booking_response.status_code != 200):
					raise Exception("failedRequest","ERROR, %d code received".format(booking_response.status_code))

				html = BeautifulSoup(booking_response.text, 'html.parser')
				num_items = extract_num_items_in_cart(html)
				if num_items == 1:
					print("Site reserved!")
					break # don't need to retry
				else:
					print("Not reserved")

				
				
			# write_response_html_to_file(booking_response, "output2.html")		


if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument("-s", "--site")
	parser.add_argument("-d", "--date")
	parser.add_argument("-l", "--length", default="14")
	parser.add_argument("-r", "--retries", default="1")
	parser.add_argument("-hr", "--hour")
	parser.add_argument("-min", "--minute")
	parser.add_argument("-sec", "--second", default="0")
	parser.add_argument("-e", "--email")
	parser.add_argument("-p", "--password")

	parser.add_argument("--use_jordan_default_time", action='store_true')

	args = parser.parse_args()
	if args.site is None or args.date is None or args.length is None or args.email is None or args.password is None:
		raise ValueError("Site, date, length, email and password must all be specified.")

	giza_bot = GizaBot()

	giza_bot.set_site(int(args.site))
	giza_bot.set_date(args.date)
	giza_bot.set_length_of_stay(args.length)
	giza_bot.set_retries(int(args.retries))

	if args.use_jordan_default_time:
		# The default time Jordan wants to use: UTC 2:59:55 pm
		giza_bot.set_time(14, 59, 55)
	elif (args.hour is not None) and (args.minute is not None):
		hour = int(args.hour)
		minute = int(args.minute)
		second = int(args.second)
		giza_bot.set_time(hour, minute, second)

	giza_bot.book_site(args.email, args.password)

