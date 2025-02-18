import requests
from collections import defaultdict
from datetime import datetime
import json
import itertools
import argparse

from twilio.rest import Client

import smtplib
import ssl


REQUEST_HEADERS = {"user-agent": "Chrome/71.0.3578.98",
        "origin": "https://www.recreation.gov",
        "authority":"www.recreation.gov",
        "referrer":"https://www.recreation.gov/camping/campgrounds/232199/availability",
        "content-type":"application/json;charset=UTF-8"}
BASE_URL = "https://www.recreation.gov/api/camps/availability/campground/232199/month"
JUNE_PARAMS = {"start_date": "2025-06-01T00:00:00.000Z"}
JULY_PARAMS = {"start_date": "2025-07-01T00:00:00.000Z"}
AUG_PARAMS = {"start_date": "2025-08-01T00:00:00.000Z"}
# The format used in dates returned by recreation.gov
WEB_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# Easier to read date format.
SHORT_DATE_FORMAT = "%m/%d"
# Reference point for counting number of days since start of the year
REF_DATE = datetime(2025,1,1)

BOOKING_URL = "https://www.recreation.gov/camping/campgrounds/232199/availability"

DEFAULT_JSON = "available.json"
DEFAULT_MIN_STAY_LENGTH = 1


def to_datetime(datestr):
        return datetime.strptime(datestr, SHORT_DATE_FORMAT)

def normalize_date(datestr):
        return datetime.strptime(datestr, WEB_DATE_FORMAT).strftime(SHORT_DATE_FORMAT)

def in_first_loop(site_number):
        return int(site_number) <= 11

def in_first_or_second_loop(site_number):
        return int(site_number) <= 24

def print_availability(d):
        for k,v in sorted(d.items(), key=lambda x: x[0]):
                print("Site {} is available on {}".format(k,", ".join(v)))

def get_jsons():
        # Get latest data from recreation.gov
        # june_resp = requests.get(BASE_URL, params=JUNE_PARAMS, headers=REQUEST_HEADERS)
        july_resp = requests.get(BASE_URL, params=JULY_PARAMS, headers=REQUEST_HEADERS)
        aug_resp = requests.get(BASE_URL, params=AUG_PARAMS, headers=REQUEST_HEADERS)
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
                        if not in_first_loop(site_number):
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
        except Exception:
                print("Couldn't load json")
                return {}

def send_sms(message, account_sid, auth_token, phone_from="", phone_list_to=[]):
        client = Client(account_sid, auth_token)
        for phone_to in phone_list_to:
                print("Sending sms to {}".format(phone_to))
                try:
                        client.messages.create(
                             body=message,
                             from_=phone_from,
                             to=phone_to)
                except Exception as e:
                        print("Unable to send sms to {}: {}".format(phone_to, e))

def send_email(subject, message_body, email_from, email_from_password, email_list_to=[]):
        port = 465
        context = ssl.create_default_context()
        message = """\
Subject: {}

{}"""
        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
                server.login(email_from, email_from_password)
                for email_to in email_list_to:
                        print("Sending email to {}".format(email_to))
                        try:
                                server.sendmail(email_from, email_to, message.format(subject, message_body))
                        except Exception as e:
                                print("Unable to send email to {0}: {1}".format(email_to, e))

def send_pushover(message, user_key, api_token):
        try:
                response = requests.post("https://api.pushover.net/1/messages.json", data={"token": api_token, "user": user_key, "message": message})
                response.raise_for_status()
                print("Pushover notification sent!")
        except Exception as e:
                print(f"Error sending Pushover notification: {e}")


def save_latest(latest, filename):
        with open(filename, 'w') as jsonfile:
                json.dump(latest, jsonfile)

if __name__ == "__main__":

        parser = argparse.ArgumentParser()
        parser.add_argument("-min", "--min_stay_length", default=DEFAULT_MIN_STAY_LENGTH, type=int)
        parser.add_argument("--json", default=DEFAULT_JSON)
        parser.add_argument("--enable_sms", action="store_true")
        parser.add_argument("-sid", "--twilio_sid")
        parser.add_argument("-auth", "--twilio_auth_token")
        parser.add_argument("--phone_from")
        parser.add_argument("--phone_to", action="append")
        parser.add_argument("--enable_email", action="store_true")
        parser.add_argument("--email_from")
        parser.add_argument("--email_from_password")
        parser.add_argument("--email_to", action="append")
        parser.add_argument("--enable_pushover", action="store_true")
        parser.add_argument("--pushover_user_key")
        parser.add_argument("--pushover_api_token")
        parser.add_argument("--test_email", default=False, type=bool)
        parser.add_argument("--test_sms", default=False, type=bool)
        parser.add_argument("--test_pushover", default=False, type=bool)
        args = parser.parse_args()
        if args.enable_sms and (
                args.twilio_sid is None or args.twilio_auth_token is None or args.phone_from is None or args.phone_to is None):
                raise ValueError("If --enable_sms is set, must provide --twilio_auth_token, --twilio_sid, --phone_from and --phone_to.")
        if args.enable_email and (args.email_from is None or args.email_to is None or args.email_from_password is None):
                raise ValueError("If --enable_email is set, must provide --email_from, --email_from_password and --email_to.")
        if args.enable_pushover and (args.pushover_user_key is None or args.pushover_api_token is None):
                raise ValueError("If --enable_pushover is set, must provide --pushover_user_key and --pushover_api_token.")

        json_file = args.json
        min_stay_length = args.min_stay_length

        # Get the most recent data
        jsons = get_jsons()
        latest_availability = load_latest_available(jsons)
        print_availability(latest_availability)

        # Get the data from the previous run
        prev_availability = load_previous(json_file)

        new_availability = get_new_availability_interval(prev_availability, latest_availability, min_stay_length)
        if not new_availability:
                print("No new availability with at least {} days.".format(min_stay_length))
        else:
                message = "New availability with {} days or more:".format(min_stay_length)
                for k,v in sorted(new_availability.items(), key=lambda x: x[0]):
                        message += "\n  Site {} on {}".format(k, ", ".join(v))
                print (message)

                if args.enable_sms:
                        sms_message = message + "\n" + BOOKING_URL
                        send_sms(sms_message, args.twilio_sid, args.twilio_auth_token, phone_from=args.phone_from, phone_list_to=args.phone_to)

                if args.enable_email:
                        subject = "New availability on {}".format(", ".join(new_availability.values()))
                        body = message + "\n\nReserve sites at " + BOOKING_URL
                        send_email(subject, body, args.email_from, args.email_from_password, email_list_to=args.email_to)

                if args.enable_pushover:
                        push_message = message + "\n" + BOOKING_URL
                        send_pushover(push_message, args.pushover_user_key, args.pushover_api_token)

        # Save data to compare against next time
        save_latest(latest_availability, json_file)
        
        if (args.test_email):
            # Send test emails
            send_email("Hello from Bartoo Bot", "This email was generated by a test run.\n\n" + BOOKING_URL, args.email_from, args.email_from_password, email_list_to=args.email_to)

        if (args.test_sms):
            # Send a test message to the first phone number
            send_sms("TEST SMS",args.twilio_sid, args.twilio_auth_token, phone_from=args.phone_from, phone_list_to=args.phone_to[:1])

        if (args.test_pushover):
            send_pushover("Hello Pushover from Bartoo! This is a test.",args.pushover_user_key, args.pushover_api_token)  
