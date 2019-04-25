from availability import *

def test_emptyCampsites():
	json1 = {"campsites" : {}}
	assert not load_latest_available([json1])

def test_noAvailabilites():
	json1 = {
		"campsites" : {
			"1": make_site("001", {})
		}
	}
	assert not load_latest_available([json1])

def test_noAvailableDates():
	json1 = {
		"campsites" : {
			"1": make_site("001", {
				"2019-08-01T00:00:00Z" : "Reserved", "2019-08-02T00:00:00Z" : "Reserved", "2019-08-03T00:00:00Z" : "Reserved"
			})
		}
	}
	assert not load_latest_available([json1])

def test_1AvailableDate():
	site_num = "001"
	json1 = {
		"campsites" : {
			"1": make_site(site_num, {
				"2019-08-01T00:00:00Z" : "Reserved", "2019-08-02T00:00:00Z" : "Available", "2019-08-03T00:00:00Z" : "Reserved"
			})
		}
	}
	latest = load_latest_available([json1])
	assert len(latest) == 1
	assert len(latest[site_num]) == 1
	assert latest[site_num][0] == "08/02"

def test_multipleAvailableDates():
	site_num = "001"
	json1 = {
		"campsites" : {
			"1": make_site(site_num, {
				"2019-08-01T00:00:00Z" : "Reserved", 
				"2019-08-02T00:00:00Z" : "Available", 
				"2019-08-03T00:00:00Z" : "Reserved", 
				"2019-08-09T00:00:00Z" : "Available"
			})
		}
	}
	latest = load_latest_available([json1])
	assert len(latest) == 1
	assert len(latest[site_num]) == 2
	assert latest[site_num][0] == "08/02"
	assert latest[site_num][1] == "08/09"

def test_getNewAvailability_none_empty():
	prev = []
	latest = []
	min_length = 1
	assert not get_site_new_availability(prev, latest, min_length)

def test_getNewAvailability_none_prevEqualsLatest():
	prev = ["8/22", "8/26"]
	latest = ["8/22", "8/26"]
	min_length = 1
	assert not get_site_new_availability(prev, latest, min_length)

def test_getNewAvailability_none_intervalTooShort():
	prev = ["8/22"]
	latest = ["8/22", "8/26"]
	min_length = 2
	assert not get_site_new_availability(prev, latest, min_length)

def test_getNewAvailability_none_intervalTooShortAndPrevEmpty():
	prev = []
	latest = ["8/22", "8/26"]
	min_length = 2
	assert not get_site_new_availability(prev, latest, min_length)

def test_getNewAvailability_minLength1():
	prev = ["8/22"]
	latest = ["8/22", "8/26"]
	min_length = 1
	new_availability = get_site_new_availability(prev, latest, min_length)
	assert len(new_availability) == 1
	assert new_availability[0] == "8/26"

def test_getNewAvailability_none_daysDifferBy1():
	prev = ["8/22"]
	latest = ["7/22", "8/23"]
	min_length = 2
	assert not get_site_new_availability(prev, latest, min_length)

def test_getNewAvailability_minLength1AndPrevEmpty():
	prev = []
	latest = ["8/22", "8/26"]
	min_length = 1
	new_availability = get_site_new_availability(prev, latest, min_length)
	assert len(new_availability) == 2
	assert new_availability[0] == "8/22"
	assert new_availability[1] == "8/26"

def test_getNewAvailability_none_adjacentPrevAndLatest():
	prev = ["7/22","8/01","8/03"]
	latest = ["7/23", "8/02"]
	min_length = 2
	assert not get_site_new_availability(prev, latest, min_length)

def test_getNewAvailability_inBetween():
	prev = ["7/22","8/01","8/03"]
	latest = ["7/23", "8/02","8/01","8/03"]
	min_length = 2
	new_availability = get_site_new_availability(prev, latest, min_length)
	assert len(new_availability) == 3


def make_site(num, av):
	site = {}
	site["site"] = num
	site["availabilities"] = av
	return site