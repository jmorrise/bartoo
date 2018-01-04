#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 20:02:39 2017

@author: jessicawise
"""
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import time
import urllib
from threading import Timer

#Constants
LUBY_BAY_PARK_ID = 70473
LUBY_BAY_CAMP_AREA = 1280981668
LENGTH_OF_STAY = 3
ARRIVAL_DATE = "6/27/2018"

# URLs
login_url = "https://www.recreation.gov/memberSignInSignUp.do"
book_site_base = "https://www.recreation.gov/switchBookingAction.do?"
search_url = "https://www.recreation.gov/unifSearchResults.do"
luby_bay_url = "https://www.recreation.gov/camping/luby-bay/r/campgroundDetails.do?contractCode=NRSO&parkId=70473"

def chrome_options(headless=True):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('headless')
    return options

class LubyBot:
    def __init__(self, site_number):
        self.site_ids = dict()
        self.site_ids[8] = 1878
        self.site_ids[3] = 1875
        self.site_ids[2] = 1870
        # Rest are for testing purposes
        self.site_ids[50] = 1845
        self.site_ids[13] = 1871
        self.site_ids[41] = 1842
        self.site_ids[42] = 1857

        self.site_number = site_number
        self.arrival_date = ARRIVAL_DATE
        self.booking_url = self.get_booking_url(self.site_number, self.arrival_date)

        

    def start(self, headless=True):
        self.browser = webdriver.Chrome("driver/chromedriver", chrome_options=chrome_options(headless=headless))
        
    def get_booking_url(self, site_number, arrival_date):
        query_params = {"contractCode":"NRSO", \
            "parkId":LUBY_BAY_PARK_ID, \
            "lengthOfStay":LENGTH_OF_STAY, \
            "dateChosen":"true", \
            "camparea":LUBY_BAY_CAMP_AREA}
            
        query_params["siteId"] = self.site_ids[site_number]
        query_params["arvdate"] = arrival_date

        return urllib.parse.unquote_plus(book_site_base + urllib.parse.urlencode(query_params))

    def login(self, _email, _password):  
        email_input_id ="AemailGroup_1733152645"
        password_input_id = "ApasswrdGroup_704558654"
        signin_button_name = "submitForm"
        
        self.browser.get(login_url)
        email_input = WebDriverWait(self.browser, 10).until(ec.presence_of_element_located((By.ID, email_input_id)))
        email_input.send_keys(_email)
        password_input = WebDriverWait(self.browser, 10).until(ec.presence_of_element_located((By.ID, password_input_id)))
        password_input.send_keys(_password)
        signin_button = self.browser.find_element_by_name(signin_button_name)
        signin_button.click()
        time.sleep(2)

    def visit_site_page(self):
        # Have to do this for some reason before booking, otherwise the requests get rejected.
        self.browser.get(luby_bay_url)

    def book_site_at_time_and_retry(self, retries, hour_, minute_, second_=0):
        if (hour_ is not None) and (minute_ is not None):
            # A time was passed in
            now = datetime.now()
            target_time = now.replace(hour=hour_, minute=minute_, second=second_, microsecond=0)
            time_delta = target_time-now
            time_delta_seconds = time_delta.total_seconds()
            # If the target time is more than 2 seconds away, set a timer.
            if time_delta_seconds > 2:
                time.sleep(time_delta_seconds-2)

            now = datetime.now()
            while (now.hour != hour_) or (now.minute != minute_) or (now.second != second_):
                time.sleep(0)
                now = datetime.now()

        for i in range(retries):
            self.book_site()
            
            print(datetime.now())
        
    def book_site(self):
        self.browser.get(self.booking_url)
        
    def sleep_until(self, hour_, minute_, second_=0):
        now = datetime.now()
        while (now.hour != hour_) or (now.minute != minute_) or (now.second != second_):
            now = datetime.now()

    def take_screenshot(self, filename):
        self.browser.get_screenshot_as_file(filename)
          
    def close(self):
        self.browser.close()

##############
# Example usage:
# luby_bay_bot.py -site=8 -hr
##############
if __name__ == "__main__":  
    # Parse input args
    parser = argparse.ArgumentParser()

    parser.add_argument("-headless", default="true")
    parser.add_argument("-site", "--site_number")
    parser.add_argument("-hr", "--hour")
    parser.add_argument("-min", "--minute")
    parser.add_argument("-sec", "--second", default="0")
    parser.add_argument("-r", "--retries", default="5") #How many times to retry
    parser.add_argument("-e", "--email")
    parser.add_argument("-p", "--password")
    args = parser.parse_args()

    run_headless = False if args.headless in ["0", "f", "false"] else True
    site_number = int(args.site_number)
    hour = int(args.hour) if args.hour else None
    minute = int(args.minute) if args.minute else None
    second = int(args.second)
    retries = int(args.retries)
    email = args.email
    password = args.password

    test_date = ARRIVAL_DATE #TODO: make this a flag

    bot = LubyBot(site_number=site_number)

    bot.start(run_headless)
    bot.login(email, password)
    bot.visit_site_page()
    bot.book_site_at_time_and_retry(retries, hour, minute, second)

    if run_headless:
        bot.take_screenshot('page.png')
        bot.close()
