import requests
from bs4 import BeautifulSoup

# URLs
UNIF_URL = "http://www.recreation.gov/unifSearchResults.do"
LOGIN_URL = "https://www.recreation.gov/memberSignInSignUp.do"
BOOKING_URL = "https://www.recreation.gov/switchBookingAction.do?"
LUBY_FULL_URL = "https://www.recreation.gov/camping/luby-bay/r/campgroundDetails.do?contractCode=NRSO&parkId=70473"

LUBY_BAY_PARK_ID = 70473
LENGTH_OF_STAY = 2
ARRIVAL_DATE = "6/17/2018"

SITE_IDS = {50:1845}

BOOKING_PAYLOAD = {"contractCode":"NRSO", 
            "parkId":LUBY_BAY_PARK_ID, 
            "lengthOfStay":LENGTH_OF_STAY, 
            "dateChosen":"true",
            "siteId":SITE_IDS[50],
            "arvdate":ARRIVAL_DATE}

def get_login_payload(email, password):
	payload = {"AemailGroup_1733152645":email,
			"ApasswrdGroup_704558654":password,
			"submitForm":"submitForm",
			"signinFromPurchaseFlow":"1",
			"sbmtCtrl":"combinedFlowSignInKit"}
	return payload

def send_request(email, password):
	with requests.Session() as s:
		login_payload = get_login_payload(email, password)
		login_response = s.post(LOGIN_URL, login_payload)
		s.get(LUBY_FULL_URL)
		booking_response = s.post(BOOKING_URL, BOOKING_PAYLOAD)

		if (booking_response.status_code != 200):
			raise Exception("failedRequest","ERROR, %d code received".format(booking_response.status_code))

		html = BeautifulSoup(booking_response.text, 'html.parser')

		with open("output.html", "w") as file:
			file.write(str(html))

		print(booking_response.headers)


if __name__ == "__main__":

	parser = argparse.ArgumentParser()

    parser.add_argument("-site", "--site_number")
    parser.add_argument("-hr", "--hour")
    parser.add_argument("-min", "--minute")
    parser.add_argument("-sec", "--second", default="0")
    parser.add_argument("-r", "--retries", default="5") #How many times to retry
    parser.add_argument("-e", "--email")
    parser.add_argument("-p", "--password")
    args = parser.parse_args()
	send_request()

