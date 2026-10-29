"""
Ground Analysis Service for CricImpact.
Aggregates historical venue scoring profiles, chase vs defend rates,
winning score benchmarks, and year-by-year trends across IPL and International T20s.
Strict adherence:
- Single source of truth.
- Does not modify existing datasets or Strategy 4 contribution formulas.
- Transparent denominators (decided matches only for defend/chase percentages).
- Separate tracking of ties, super overs, no-results, and DLS rain adjustments.
"""

import datetime
import logging
import math
import threading
import urllib.parse
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from app.services.data_service import data_service

logger = logging.getLogger(__name__)

# Pre-verified DLS rain-affected matches across active IPL and T20I datasets
DLS_MATCH_IDS = {
    # IPL DLS matches
    "336022", "336025", "392186", "392188", "419131", "501215", "501245", "501258",
    "548329", "729315", "829743", "829793", "829807", "829813", "829823", "980997",
    "980999", "1082648", "1136566", "1136578", "1136592", "1359476", "1370353",
    # T20I DLS matches
    "1295349", "1303312", "1317489", "1322277", "1322278", "1322280", "1322329",
    "1322330", "1336128", "1348649", "1373574", "1383088", "1384394", "1389387",
    "1405374", "1411181", "1415730", "1425126", "1426462", "1430030", "1432427",
    "1433367", "1441324"
}

# Pre-verified Ties / Super-Over matches across active IPL and T20I datasets
SUPER_OVER_MATCH_IDS = {
    # IPL
    "392190", "419121", "598004", "598017", "729307", "729315", "829741", "1082625",
    "1175365", "1178426", "1216493", "1216512", "1216517", "1216547", "1254077", "1254101",
    # T20I
    "1298160", "1321477", "1343743", "1359544", "1405377", "1415732", "1496937"
}

# Pre-verified No-Result / Abandoned matches across active IPL and T20I datasets
NO_RESULT_MATCH_IDS = {
    # IPL
    "501265", "829763", "829771", "980961", "1178424", "1254104", "1359519", "1422137", "1426297",
    # T20I
    "1298161", "1317490", "1322279", "1322281", "1322331", "1336129", "1373575", "1383089",
    "1384395", "1389388", "1411182", "1425127", "1430031", "1441325", "1467706", "1478907",
    "1478911", "1491715", "1491717", "1491719", "1491726", "1496574", "1498664"
}

# Verified Canonical Venue definitions and raw aliases mapping
CANONICAL_VENUE_DEFINITIONS = {
    "Wankhede Stadium, Mumbai": {
        "canonical_name": "Wankhede Stadium, Mumbai",
        "city": "Mumbai",
        "country": "India",
        "aliases": ["Wankhede Stadium", "Wankhede Stadium, Mumbai"],
    },
    "Eden Gardens, Kolkata": {
        "canonical_name": "Eden Gardens, Kolkata",
        "city": "Kolkata",
        "country": "India",
        "aliases": ["Eden Gardens", "Eden Gardens, Kolkata"],
    },
    "M Chinnaswamy Stadium, Bengaluru": {
        "canonical_name": "M Chinnaswamy Stadium, Bengaluru",
        "city": "Bengaluru",
        "country": "India",
        "aliases": [
            "M Chinnaswamy Stadium",
            "M Chinnaswamy Stadium, Bangalore",
            "M Chinnaswamy Stadium, Bengaluru",
            "M.Chinnaswamy Stadium",
        ],
    },
    "MA Chidambaram Stadium, Chepauk, Chennai": {
        "canonical_name": "MA Chidambaram Stadium, Chepauk, Chennai",
        "city": "Chennai",
        "country": "India",
        "aliases": [
            "MA Chidambaram Stadium",
            "MA Chidambaram Stadium, Chepauk",
            "MA Chidambaram Stadium, Chepauk, Chennai",
        ],
    },
    "Arun Jaitley Stadium, Delhi": {
        "canonical_name": "Arun Jaitley Stadium, Delhi",
        "city": "Delhi",
        "country": "India",
        "aliases": ["Arun Jaitley Stadium", "Arun Jaitley Stadium, Delhi"],
    },
    "Feroz Shah Kotla, Delhi": {
        "canonical_name": "Feroz Shah Kotla, Delhi",
        "city": "Delhi",
        "country": "India",
        "aliases": ["Feroz Shah Kotla"],
    },
    "Rajiv Gandhi International Stadium, Hyderabad": {
        "canonical_name": "Rajiv Gandhi International Stadium, Hyderabad",
        "city": "Hyderabad",
        "country": "India",
        "aliases": [
            "Rajiv Gandhi International Stadium",
            "Rajiv Gandhi International Stadium, Uppal",
            "Rajiv Gandhi International Stadium, Uppal, Hyderabad",
        ],
    },
    "Punjab Cricket Association IS Bindra Stadium, Mohali": {
        "canonical_name": "Punjab Cricket Association IS Bindra Stadium, Mohali",
        "city": "Chandigarh",
        "country": "India",
        "aliases": [
            "Punjab Cricket Association Stadium, Mohali",
            "Punjab Cricket Association IS Bindra Stadium",
            "Punjab Cricket Association IS Bindra Stadium, Mohali",
            "Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh",
        ],
    },
    "Narendra Modi Stadium, Ahmedabad": {
        "canonical_name": "Narendra Modi Stadium, Ahmedabad",
        "city": "Ahmedabad",
        "country": "India",
        "aliases": ["Narendra Modi Stadium, Ahmedabad"],
    },
    "Sardar Patel Stadium, Motera": {
        "canonical_name": "Sardar Patel Stadium, Motera",
        "city": "Ahmedabad",
        "country": "India",
        "aliases": ["Sardar Patel Stadium, Motera"],
    },
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow": {
        "canonical_name": "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow",
        "city": "Lucknow",
        "country": "India",
        "aliases": ["Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"],
    },
    "Brabourne Stadium, Mumbai": {
        "canonical_name": "Brabourne Stadium, Mumbai",
        "city": "Mumbai",
        "country": "India",
        "aliases": ["Brabourne Stadium", "Brabourne Stadium, Mumbai"],
    },
    "Dr DY Patil Sports Academy, Mumbai": {
        "canonical_name": "Dr DY Patil Sports Academy, Mumbai",
        "city": "Mumbai",
        "country": "India",
        "aliases": ["Dr DY Patil Sports Academy", "Dr DY Patil Sports Academy, Mumbai"],
    },
    "Himachal Pradesh Cricket Association Stadium, Dharamsala": {
        "canonical_name": "Himachal Pradesh Cricket Association Stadium, Dharamsala",
        "city": "Dharamsala",
        "country": "India",
        "aliases": [
            "Himachal Pradesh Cricket Association Stadium",
            "Himachal Pradesh Cricket Association Stadium, Dharamsala",
        ],
    },
    "Holkar Cricket Stadium, Indore": {
        "canonical_name": "Holkar Cricket Stadium, Indore",
        "city": "Indore",
        "country": "India",
        "aliases": ["Holkar Cricket Stadium", "Holkar Cricket Stadium, Indore"],
    },
    "Sawai Mansingh Stadium, Jaipur": {
        "canonical_name": "Sawai Mansingh Stadium, Jaipur",
        "city": "Jaipur",
        "country": "India",
        "aliases": ["Sawai Mansingh Stadium", "Sawai Mansingh Stadium, Jaipur"],
    },
    "Maharashtra Cricket Association Stadium, Pune": {
        "canonical_name": "Maharashtra Cricket Association Stadium, Pune",
        "city": "Pune",
        "country": "India",
        "aliases": ["Maharashtra Cricket Association Stadium", "Maharashtra Cricket Association Stadium, Pune"],
    },
    "Subrata Roy Sahara Stadium, Pune": {
        "canonical_name": "Subrata Roy Sahara Stadium, Pune",
        "city": "Pune",
        "country": "India",
        "aliases": ["Subrata Roy Sahara Stadium"],
    },
    "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur": {
        "canonical_name": "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur",
        "city": "New Chandigarh",
        "country": "India",
        "aliases": [
            "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur",
            "Maharaja Yadavindra Singh International Cricket Stadium, New Chandigarh",
        ],
    },
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam": {
        "canonical_name": "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam",
        "city": "Visakhapatnam",
        "country": "India",
        "aliases": [
            "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium",
            "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam",
        ],
    },
    "Barsapara Cricket Stadium, Guwahati": {
        "canonical_name": "Barsapara Cricket Stadium, Guwahati",
        "city": "Guwahati",
        "country": "India",
        "aliases": ["Barsapara Cricket Stadium, Guwahati"],
    },
    "Barabati Stadium, Cuttack": {
        "canonical_name": "Barabati Stadium, Cuttack",
        "city": "Cuttack",
        "country": "India",
        "aliases": ["Barabati Stadium", "Barabati Stadium, Cuttack"],
    },
    "JSCA International Stadium Complex, Ranchi": {
        "canonical_name": "JSCA International Stadium Complex, Ranchi",
        "city": "Ranchi",
        "country": "India",
        "aliases": ["JSCA International Stadium Complex", "JSCA International Stadium Complex, Ranchi"],
    },
    "Saurashtra Cricket Association Stadium, Rajkot": {
        "canonical_name": "Saurashtra Cricket Association Stadium, Rajkot",
        "city": "Rajkot",
        "country": "India",
        "aliases": ["Saurashtra Cricket Association Stadium", "Saurashtra Cricket Association Stadium, Rajkot"],
    },
    "Shaheed Veer Narayan Singh International Stadium, Raipur": {
        "canonical_name": "Shaheed Veer Narayan Singh International Stadium, Raipur",
        "city": "Raipur",
        "country": "India",
        "aliases": [
            "Shaheed Veer Narayan Singh International Stadium",
            "Shaheed Veer Narayan Singh International Stadium, Raipur",
        ],
    },
    "Vidarbha Cricket Association Stadium, Jamtha, Nagpur": {
        "canonical_name": "Vidarbha Cricket Association Stadium, Jamtha, Nagpur",
        "city": "Nagpur",
        "country": "India",
        "aliases": [
            "Vidarbha Cricket Association Stadium, Jamtha",
            "Vidarbha Cricket Association Stadium, Jamtha, Nagpur",
        ],
    },
    "Greenfield International Stadium, Thiruvananthapuram": {
        "canonical_name": "Greenfield International Stadium, Thiruvananthapuram",
        "city": "Thiruvananthapuram",
        "country": "India",
        "aliases": ["Greenfield International Stadium, Thiruvananthapuram"],
    },
    "Green Park, Kanpur": {
        "canonical_name": "Green Park, Kanpur",
        "city": "Kanpur",
        "country": "India",
        "aliases": ["Green Park"],
    },
    "Nehru Stadium, Kochi": {
        "canonical_name": "Nehru Stadium, Kochi",
        "city": "Kochi",
        "country": "India",
        "aliases": ["Nehru Stadium"],
    },
    "Shrimant Madhavrao Scindia Cricket Stadium, Gwalior": {
        "canonical_name": "Shrimant Madhavrao Scindia Cricket Stadium, Gwalior",
        "city": "Gwalior",
        "country": "India",
        "aliases": ["Shrimant Madhavrao Scindia Cricket Stadium, Gwalior"],
    },
    # UAE
    "Dubai International Cricket Stadium": {
        "canonical_name": "Dubai International Cricket Stadium",
        "city": "Dubai",
        "country": "United Arab Emirates",
        "aliases": ["Dubai International Cricket Stadium"],
    },
    "Sharjah Cricket Stadium": {
        "canonical_name": "Sharjah Cricket Stadium",
        "city": "Sharjah",
        "country": "United Arab Emirates",
        "aliases": ["Sharjah Cricket Stadium"],
    },
    "Zayed Cricket Stadium, Abu Dhabi": {
        "canonical_name": "Zayed Cricket Stadium, Abu Dhabi",
        "city": "Abu Dhabi",
        "country": "United Arab Emirates",
        "aliases": ["Sheikh Zayed Stadium", "Zayed Cricket Stadium, Abu Dhabi"],
    },
    "7he Sevens Stadium, Dubai": {
        "canonical_name": "7he Sevens Stadium, Dubai",
        "city": "Dubai",
        "country": "United Arab Emirates",
        "aliases": ["7he Sevens Stadium, Dubai"],
    },
    # Australia
    "Melbourne Cricket Ground": {
        "canonical_name": "Melbourne Cricket Ground",
        "city": "Melbourne",
        "country": "Australia",
        "aliases": ["Melbourne Cricket Ground"],
    },
    "Sydney Cricket Ground": {
        "canonical_name": "Sydney Cricket Ground",
        "city": "Sydney",
        "country": "Australia",
        "aliases": ["Sydney Cricket Ground"],
    },
    "Adelaide Oval": {
        "canonical_name": "Adelaide Oval",
        "city": "Adelaide",
        "country": "Australia",
        "aliases": ["Adelaide Oval"],
    },
    "Perth Stadium": {
        "canonical_name": "Perth Stadium",
        "city": "Perth",
        "country": "Australia",
        "aliases": ["Perth Stadium"],
    },
    "Brisbane Cricket Ground, Woolloongabba, Brisbane": {
        "canonical_name": "Brisbane Cricket Ground, Woolloongabba, Brisbane",
        "city": "Brisbane",
        "country": "Australia",
        "aliases": ["Brisbane Cricket Ground, Woolloongabba, Brisbane"],
    },
    "Bellerive Oval, Hobart": {
        "canonical_name": "Bellerive Oval, Hobart",
        "city": "Hobart",
        "country": "Australia",
        "aliases": ["Bellerive Oval, Hobart"],
    },
    "Manuka Oval, Canberra": {
        "canonical_name": "Manuka Oval, Canberra",
        "city": "Canberra",
        "country": "Australia",
        "aliases": ["Manuka Oval, Canberra"],
    },
    "GMHBA Stadium, South Geelong, Victoria": {
        "canonical_name": "GMHBA Stadium, South Geelong, Victoria",
        "city": "Geelong",
        "country": "Australia",
        "aliases": ["GMHBA Stadium, South Geelong, Victoria"],
    },
    "Carrara Oval": {
        "canonical_name": "Carrara Oval",
        "city": "Carrara",
        "country": "Australia",
        "aliases": ["Carrara Oval"],
    },
    "Cazaly's Stadium, Cairns": {
        "canonical_name": "Cazaly's Stadium, Cairns",
        "city": "Cairns",
        "country": "Australia",
        "aliases": ["Cazaly's Stadium, Cairns"],
    },
    "Marrara Stadium, Darwin": {
        "canonical_name": "Marrara Stadium, Darwin",
        "city": "Darwin",
        "country": "Australia",
        "aliases": ["Marrara Stadium, Darwin"],
    },
    # England & Wales
    "Kennington Oval, London": {
        "canonical_name": "Kennington Oval, London",
        "city": "London",
        "country": "England",
        "aliases": ["Kennington Oval, London"],
    },
    "Edgbaston, Birmingham": {
        "canonical_name": "Edgbaston, Birmingham",
        "city": "Birmingham",
        "country": "England",
        "aliases": ["Edgbaston, Birmingham"],
    },
    "Old Trafford, Manchester": {
        "canonical_name": "Old Trafford, Manchester",
        "city": "Manchester",
        "country": "England",
        "aliases": ["Old Trafford", "Old Trafford, Manchester"],
    },
    "Trent Bridge, Nottingham": {
        "canonical_name": "Trent Bridge, Nottingham",
        "city": "Nottingham",
        "country": "England",
        "aliases": ["Trent Bridge, Nottingham"],
    },
    "The Rose Bowl, Southampton": {
        "canonical_name": "The Rose Bowl, Southampton",
        "city": "Southampton",
        "country": "England",
        "aliases": ["The Rose Bowl, Southampton"],
    },
    "County Ground, Bristol": {
        "canonical_name": "County Ground, Bristol",
        "city": "Bristol",
        "country": "England",
        "aliases": ["County Ground, Bristol"],
    },
    "Riverside Ground, Chester-le-Street": {
        "canonical_name": "Riverside Ground, Chester-le-Street",
        "city": "Chester-le-Street",
        "country": "England",
        "aliases": ["Riverside Ground, Chester-le-Street"],
    },
    "Sophia Gardens, Cardiff": {
        "canonical_name": "Sophia Gardens, Cardiff",
        "city": "Cardiff",
        "country": "Wales",
        "aliases": ["Sophia Gardens, Cardiff"],
    },
    # South Africa
    "The Wanderers Stadium, Johannesburg": {
        "canonical_name": "The Wanderers Stadium, Johannesburg",
        "city": "Johannesburg",
        "country": "South Africa",
        "aliases": ["New Wanderers Stadium", "The Wanderers Stadium, Johannesburg"],
    },
    "Newlands, Cape Town": {
        "canonical_name": "Newlands, Cape Town",
        "city": "Cape Town",
        "country": "South Africa",
        "aliases": ["Newlands"],
    },
    "Kingsmead, Durban": {
        "canonical_name": "Kingsmead, Durban",
        "city": "Durban",
        "country": "South Africa",
        "aliases": ["Kingsmead", "Kingsmead, Durban"],
    },
    "SuperSport Park, Centurion": {
        "canonical_name": "SuperSport Park, Centurion",
        "city": "Centurion",
        "country": "South Africa",
        "aliases": ["SuperSport Park", "SuperSport Park, Centurion"],
    },
    "St George's Park, Gqeberha": {
        "canonical_name": "St George's Park, Gqeberha",
        "city": "Gqeberha",
        "country": "South Africa",
        "aliases": ["St George's Park", "St George's Park, Gqeberha"],
    },
    "Boland Park, Paarl": {
        "canonical_name": "Boland Park, Paarl",
        "city": "Paarl",
        "country": "South Africa",
        "aliases": ["Boland Park, Paarl"],
    },
    "Buffalo Park, East London": {
        "canonical_name": "Buffalo Park, East London",
        "city": "East London",
        "country": "South Africa",
        "aliases": ["Buffalo Park"],
    },
    "De Beers Diamond Oval, Kimberley": {
        "canonical_name": "De Beers Diamond Oval, Kimberley",
        "city": "Kimberley",
        "country": "South Africa",
        "aliases": ["De Beers Diamond Oval"],
    },
    "OUTsurance Oval, Bloemfontein": {
        "canonical_name": "OUTsurance Oval, Bloemfontein",
        "city": "Bloemfontein",
        "country": "South Africa",
        "aliases": ["OUTsurance Oval"],
    },
    # New Zealand
    "Eden Park, Auckland": {
        "canonical_name": "Eden Park, Auckland",
        "city": "Auckland",
        "country": "New Zealand",
        "aliases": ["Eden Park, Auckland"],
    },
    "Sky Stadium, Wellington": {
        "canonical_name": "Sky Stadium, Wellington",
        "city": "Wellington",
        "country": "New Zealand",
        "aliases": ["Sky Stadium, Wellington"],
    },
    "Hagley Oval, Christchurch": {
        "canonical_name": "Hagley Oval, Christchurch",
        "city": "Christchurch",
        "country": "New Zealand",
        "aliases": ["Hagley Oval, Christchurch"],
    },
    "Seddon Park, Hamilton": {
        "canonical_name": "Seddon Park, Hamilton",
        "city": "Hamilton",
        "country": "New Zealand",
        "aliases": ["Seddon Park, Hamilton"],
    },
    "Bay Oval, Mount Maunganui": {
        "canonical_name": "Bay Oval, Mount Maunganui",
        "city": "Mount Maunganui",
        "country": "New Zealand",
        "aliases": ["Bay Oval, Mount Maunganui"],
    },
    "McLean Park, Napier": {
        "canonical_name": "McLean Park, Napier",
        "city": "Napier",
        "country": "New Zealand",
        "aliases": ["McLean Park, Napier"],
    },
    "University Oval, Dunedin": {
        "canonical_name": "University Oval, Dunedin",
        "city": "Dunedin",
        "country": "New Zealand",
        "aliases": ["University Oval, Dunedin"],
    },
    "John Davies Oval, Queenstown": {
        "canonical_name": "John Davies Oval, Queenstown",
        "city": "Queenstown",
        "country": "New Zealand",
        "aliases": ["John Davies Oval, Queenstown"],
    },
    "Saxton Oval, Nelson": {
        "canonical_name": "Saxton Oval, Nelson",
        "city": "Nelson",
        "country": "New Zealand",
        "aliases": ["Saxton Oval, Nelson"],
    },
    # West Indies
    "Kensington Oval, Bridgetown, Barbados": {
        "canonical_name": "Kensington Oval, Bridgetown, Barbados",
        "city": "Bridgetown",
        "country": "West Indies",
        "aliases": ["Kensington Oval, Bridgetown, Barbados"],
    },
    "Brian Lara Stadium, Tarouba, Trinidad": {
        "canonical_name": "Brian Lara Stadium, Tarouba, Trinidad",
        "city": "Tarouba",
        "country": "West Indies",
        "aliases": ["Brian Lara Stadium, Tarouba, Trinidad"],
    },
    "Daren Sammy National Cricket Stadium, Gros Islet, St Lucia": {
        "canonical_name": "Daren Sammy National Cricket Stadium, Gros Islet, St Lucia",
        "city": "Gros Islet",
        "country": "West Indies",
        "aliases": ["Daren Sammy National Cricket Stadium, Gros Islet, St Lucia"],
    },
    "Providence Stadium, Guyana": {
        "canonical_name": "Providence Stadium, Guyana",
        "city": "Providence",
        "country": "West Indies",
        "aliases": ["Providence Stadium, Guyana"],
    },
    "Sir Vivian Richards Stadium, North Sound, Antigua": {
        "canonical_name": "Sir Vivian Richards Stadium, North Sound, Antigua",
        "city": "North Sound",
        "country": "West Indies",
        "aliases": ["Sir Vivian Richards Stadium, North Sound, Antigua"],
    },
    "Arnos Vale Ground, Kingstown, St Vincent": {
        "canonical_name": "Arnos Vale Ground, Kingstown, St Vincent",
        "city": "Kingstown",
        "country": "West Indies",
        "aliases": ["Arnos Vale Ground, Kingstown, St Vincent"],
    },
    "National Cricket Stadium, St George's, Grenada": {
        "canonical_name": "National Cricket Stadium, St George's, Grenada",
        "city": "St George's",
        "country": "West Indies",
        "aliases": ["National Cricket Stadium, St George's, Grenada"],
    },
    "Sabina Park, Kingston, Jamaica": {
        "canonical_name": "Sabina Park, Kingston, Jamaica",
        "city": "Kingston",
        "country": "West Indies",
        "aliases": ["Sabina Park, Kingston, Jamaica"],
    },
    "Warner Park, Basseterre, St Kitts": {
        "canonical_name": "Warner Park, Basseterre, St Kitts",
        "city": "Basseterre",
        "country": "West Indies",
        "aliases": ["Warner Park, Basseterre, St Kitts"],
    },
    "Windsor Park, Roseau, Dominica": {
        "canonical_name": "Windsor Park, Roseau, Dominica",
        "city": "Roseau",
        "country": "West Indies",
        "aliases": ["Windsor Park, Roseau, Dominica"],
    },
    # Sri Lanka
    "R Premadasa Stadium, Colombo": {
        "canonical_name": "R Premadasa Stadium, Colombo",
        "city": "Colombo",
        "country": "Sri Lanka",
        "aliases": ["R Premadasa Stadium, Colombo"],
    },
    "Pallekele International Cricket Stadium": {
        "canonical_name": "Pallekele International Cricket Stadium",
        "city": "Kandy",
        "country": "Sri Lanka",
        "aliases": ["Pallekele International Cricket Stadium"],
    },
    "Rangiri Dambulla International Stadium": {
        "canonical_name": "Rangiri Dambulla International Stadium",
        "city": "Dambulla",
        "country": "Sri Lanka",
        "aliases": ["Rangiri Dambulla International Stadium"],
    },
    "Sinhalese Sports Club Ground, Colombo": {
        "canonical_name": "Sinhalese Sports Club Ground, Colombo",
        "city": "Colombo",
        "country": "Sri Lanka",
        "aliases": ["Sinhalese Sports Club Ground, Colombo"],
    },
    # Pakistan
    "Gaddafi Stadium, Lahore": {
        "canonical_name": "Gaddafi Stadium, Lahore",
        "city": "Lahore",
        "country": "Pakistan",
        "aliases": ["Gaddafi Stadium, Lahore"],
    },
    "National Stadium, Karachi": {
        "canonical_name": "National Stadium, Karachi",
        "city": "Karachi",
        "country": "Pakistan",
        "aliases": ["National Stadium, Karachi"],
    },
    "Rawalpindi Cricket Stadium": {
        "canonical_name": "Rawalpindi Cricket Stadium",
        "city": "Rawalpindi",
        "country": "Pakistan",
        "aliases": ["Rawalpindi Cricket Stadium"],
    },
    # Bangladesh
    "Shere Bangla National Stadium, Mirpur": {
        "canonical_name": "Shere Bangla National Stadium, Mirpur",
        "city": "Dhaka",
        "country": "Bangladesh",
        "aliases": ["Shere Bangla National Stadium, Mirpur"],
    },
    "Zahur Ahmed Chowdhury Stadium, Chattogram": {
        "canonical_name": "Zahur Ahmed Chowdhury Stadium, Chattogram",
        "city": "Chattogram",
        "country": "Bangladesh",
        "aliases": ["Zahur Ahmed Chowdhury Stadium, Chattogram"],
    },
    "Bir Sreshtho Flight Lieutenant Matiur Rahman Stadium, Chattogram": {
        "canonical_name": "Bir Sreshtho Flight Lieutenant Matiur Rahman Stadium, Chattogram",
        "city": "Chattogram",
        "country": "Bangladesh",
        "aliases": ["Bir Sreshtho Flight Lieutenant Matiur Rahman Stadium, Chattogram"],
    },
    "Sylhet International Cricket Stadium": {
        "canonical_name": "Sylhet International Cricket Stadium",
        "city": "Sylhet",
        "country": "Bangladesh",
        "aliases": ["Sylhet International Cricket Stadium"],
    },
    # USA
    "Central Broward Regional Park Stadium Turf Ground, Lauderhill": {
        "canonical_name": "Central Broward Regional Park Stadium Turf Ground, Lauderhill",
        "city": "Lauderhill",
        "country": "USA",
        "aliases": ["Central Broward Regional Park Stadium Turf Ground, Lauderhill"],
    },
    "Grand Prairie Stadium, Dallas": {
        "canonical_name": "Grand Prairie Stadium, Dallas",
        "city": "Dallas",
        "country": "USA",
        "aliases": ["Grand Prairie Stadium, Dallas"],
    },
    "Nassau County International Cricket Stadium, New York": {
        "canonical_name": "Nassau County International Cricket Stadium, New York",
        "city": "New York",
        "country": "USA",
        "aliases": ["Nassau County International Cricket Stadium, New York"],
    },
    "Prairie View Cricket Complex": {
        "canonical_name": "Prairie View Cricket Complex",
        "city": "Houston",
        "country": "USA",
        "aliases": ["Prairie View Cricket Complex"],
    },
    # Ireland
    "The Village, Malahide, Dublin": {
        "canonical_name": "The Village, Malahide, Dublin",
        "city": "Dublin",
        "country": "Ireland",
        "aliases": ["Malahide, Dublin", "The Village, Malahide, Dublin"],
    },
    "Civil Service Cricket Club, Stormont, Belfast": {
        "canonical_name": "Civil Service Cricket Club, Stormont, Belfast",
        "city": "Belfast",
        "country": "Ireland",
        "aliases": ["Civil Service Cricket Club, Stormont, Belfast"],
    },
    "Castle Avenue, Dublin": {
        "canonical_name": "Castle Avenue, Dublin",
        "city": "Dublin",
        "country": "Ireland",
        "aliases": ["Castle Avenue, Dublin"],
    },
    "Bready Cricket Club, Magheramason, Bready": {
        "canonical_name": "Bready Cricket Club, Magheramason, Bready",
        "city": "Bready",
        "country": "Ireland",
        "aliases": ["Bready Cricket Club, Magheramason, Bready"],
    },
    # Zimbabwe
    "Harare Sports Club": {
        "canonical_name": "Harare Sports Club",
        "city": "Harare",
        "country": "Zimbabwe",
        "aliases": ["Harare Sports Club"],
    },
    "Queens Sports Club, Bulawayo": {
        "canonical_name": "Queens Sports Club, Bulawayo",
        "city": "Bulawayo",
        "country": "Zimbabwe",
        "aliases": ["Queens Sports Club, Bulawayo"],
    },
    "Bulawayo Athletic Club": {
        "canonical_name": "Bulawayo Athletic Club",
        "city": "Bulawayo",
        "country": "Zimbabwe",
        "aliases": ["Bulawayo Athletic Club"],
    },
    # Scotland
    "Grange Cricket Club Ground, Raeburn Place, Edinburgh": {
        "canonical_name": "Grange Cricket Club Ground, Raeburn Place, Edinburgh",
        "city": "Edinburgh",
        "country": "Scotland",
        "aliases": ["Grange Cricket Club Ground, Raeburn Place, Edinburgh"],
    },
    "Goldenacre, Edinburgh": {
        "canonical_name": "Goldenacre, Edinburgh",
        "city": "Edinburgh",
        "country": "Scotland",
        "aliases": ["Goldenacre, Edinburgh"],
    },
    "Titwood, Glasgow": {
        "canonical_name": "Titwood, Glasgow",
        "city": "Glasgow",
        "country": "Scotland",
        "aliases": ["Titwood, Glasgow"],
    },
    # Netherlands
    "Sportpark Westvliet, The Hague": {
        "canonical_name": "Sportpark Westvliet, The Hague",
        "city": "The Hague",
        "country": "Netherlands",
        "aliases": ["Sportpark Westvliet, The Hague", "Sportpark Westvliet, Voorburg"],
    },
    "Sportpark Maarschalkerweerd, Utrecht": {
        "canonical_name": "Sportpark Maarschalkerweerd, Utrecht",
        "city": "Utrecht",
        "country": "Netherlands",
        "aliases": ["Sportpark Maarschalkerweerd, Utrecht"],
    },
    # Oman
    "Al Amerat Cricket Ground Oman Cricket (Ministry Turf 1)": {
        "canonical_name": "Al Amerat Cricket Ground Oman Cricket (Ministry Turf 1)",
        "city": "Al Amarat",
        "country": "Oman",
        "aliases": ["Al Amerat Cricket Ground Oman Cricket (Ministry Turf 1)"],
    },
    "Al Amerat Cricket Ground Oman Cricket (Ministry Turf 2)": {
        "canonical_name": "Al Amerat Cricket Ground Oman Cricket (Ministry Turf 2)",
        "city": "Al Amarat",
        "country": "Oman",
        "aliases": ["Al Amerat Cricket Ground Oman Cricket (Ministry Turf 2)"],
    },
    # Namibia
    "Namibia Cricket Ground, Windhoek": {
        "canonical_name": "Namibia Cricket Ground, Windhoek",
        "city": "Windhoek",
        "country": "Namibia",
        "aliases": ["Namibia Cricket Ground, Windhoek"],
    },
    "United Cricket Club Ground, Windhoek": {
        "canonical_name": "United Cricket Club Ground, Windhoek",
        "city": "Windhoek",
        "country": "Namibia",
        "aliases": ["United Cricket Club Ground, Windhoek"],
    },
    "Wanderers Cricket Ground, Windhoek": {
        "canonical_name": "Wanderers Cricket Ground, Windhoek",
        "city": "Windhoek",
        "country": "Namibia",
        "aliases": ["Wanderers Cricket Ground, Windhoek"],
    },
    # Kenya
    "Gymkhana Club Ground, Nairobi": {
        "canonical_name": "Gymkhana Club Ground, Nairobi",
        "city": "Nairobi",
        "country": "Kenya",
        "aliases": ["Gymkhana Club Ground, Nairobi"],
    },
    "Ruaraka Sports Club Ground, Nairobi": {
        "canonical_name": "Ruaraka Sports Club Ground, Nairobi",
        "city": "Nairobi",
        "country": "Kenya",
        "aliases": ["Ruaraka Sports Club Ground, Nairobi"],
    },
    # Japan
    "Sano International Cricket Ground": {
        "canonical_name": "Sano International Cricket Ground",
        "city": "Sano",
        "country": "Japan",
        "aliases": ["Sano International Cricket Ground"],
    },
    "Korogi Sports Park": {
        "canonical_name": "Korogi Sports Park",
        "city": "Nisshin",
        "country": "Japan",
        "aliases": ["Korogi Sports Park"],
    },
    # Ghana
    "Achimota Senior Secondary School A Field, Accra": {
        "canonical_name": "Achimota Senior Secondary School A Field, Accra",
        "city": "Accra",
        "country": "Ghana",
        "aliases": ["Achimota Senior Secondary School A Field, Accra"],
    },
    # China
    "Zhejiang University of Technology Cricket Field": {
        "canonical_name": "Zhejiang University of Technology Cricket Field",
        "city": "Hangzhou",
        "country": "China",
        "aliases": ["Zhejiang University of Technology Cricket Field"],
    },
    # Cayman Islands
    "Jimmy Powell Oval, Cayman Islands": {
        "canonical_name": "Jimmy Powell Oval, Cayman Islands",
        "city": "George Town",
        "country": "Cayman Islands",
        "aliases": ["Jimmy Powell Oval, Cayman Islands"],
    },
}

# Invert aliases for fast O(1) canonical venue resolution
RAW_TO_CANONICAL: Dict[str, str] = {}
for canon, d in CANONICAL_VENUE_DEFINITIONS.items():
    for alias in d["aliases"]:
        RAW_TO_CANONICAL[alias.strip()] = canon


def clean_num(val, decimals: Optional[int] = None):
    if val is None or pd.isna(val) or val == "" or str(val).strip().lower() in ("nan", "none", "null"):
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        if decimals is not None:
            return round(f, decimals)
        return f
    except (ValueError, TypeError):
        return None


class GroundAnalysisService:
    def __init__(self):
        self._matches_cache: Optional[List[Dict[str, Any]]] = None
        self._venues_index: Optional[Dict[str, Dict[str, Any]]] = None
        self._phases_data: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    def _ensure_phases_loaded(self):
        if self._phases_data is not None:
            return
        import json
        from pathlib import Path
        
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "phase_summaries.json",
            Path.cwd() / "data" / "processed" / "phase_summaries.json",
            Path(__file__).resolve().parents[2] / "data" / "processed" / "phase_summaries.json",
        ]
        
        target_path = None
        for candidate in candidates:
            if candidate.exists():
                target_path = candidate
                break
                
        if target_path is not None:
            try:
                with open(target_path, "r", encoding="utf-8") as fp:
                    self._phases_data = json.load(fp)
                logger.info(
                    "Loaded phase summaries from %s (%d matches indexed)",
                    target_path,
                    len(self._phases_data.get("phases", {})),
                )
            except Exception as e:
                logger.error("Failed to parse phase summaries at %s: %s", target_path, e)
                self._phases_data = {"conditions": {}, "phases": {}}
        else:
            logger.warning(
                "Phase summaries file not found in search paths: %s. Phase statistics will be unavailable.",
                [str(c) for c in candidates],
            )
            self._phases_data = {"conditions": {}, "phases": {}}

    def _ensure_indexed(self):
        if self._matches_cache is not None:
            return

        with self._lock:
            if self._matches_cache is not None:
                return

            self._ensure_phases_loaded()
            conditions_map = self._phases_data.get("conditions", {})

            all_records = []
            raw_to_canon = RAW_TO_CANONICAL

            # 1. Process IPL matches and innings
            data_service._ensure_loaded("ipl")
            ipl_m = data_service.get_matches_df("ipl")
            inn_ipl = data_service._cache["ipl"].get("innings")
            if inn_ipl is None:
                from pathlib import Path
                p_inn = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "innings.csv"
                if p_inn.exists():
                    inn_ipl = pd.read_csv(p_inn)
                else:
                    inn_ipl = pd.DataFrame()

            ipl_inn_dict = {}
            if inn_ipl is not None and not inn_ipl.empty:
                for r in inn_ipl.to_dict("records"):
                    mid = str(r["match_id"])
                    if mid not in ipl_inn_dict:
                        ipl_inn_dict[mid] = {"inn1": None, "inn2": None}
                    in_num = r.get("innings_number")
                    if in_num == 1:
                        ipl_inn_dict[mid]["inn1"] = r
                    elif in_num == 2:
                        ipl_inn_dict[mid]["inn2"] = r

            if ipl_m is not None and not ipl_m.empty:
                for r in ipl_m.to_dict("records"):
                    mid = str(r["match_id"])
                    raw_venue = str(r.get("venue", "")).strip()
                    canon_venue = raw_to_canon.get(raw_venue, raw_venue)
                    v_def = CANONICAL_VENUE_DEFINITIONS.get(canon_venue, {
                        "canonical_name": canon_venue,
                        "city": str(r.get("city", "Unknown")),
                        "country": "India" if "India" in canon_venue else "Other / Unspecified",
                    })

                    d_str = str(r.get("date", ""))
                    if len(d_str) >= 10 and d_str[4] == "-" and d_str[7] == "-":
                        yr = int(d_str[:4])
                        formatted_date = d_str[:10]
                    else:
                        try:
                            dt = pd.to_datetime(d_str)
                            yr = int(dt.year)
                            formatted_date = dt.strftime("%Y-%m-%d")
                        except Exception:
                            yr = 2008
                            formatted_date = d_str

                    inn_info = ipl_inn_dict.get(mid, {})
                    inn1_raw = inn_info.get("inn1")
                    inn2_raw = inn_info.get("inn2")

                    winner = str(r.get("winner")) if pd.notnull(r.get("winner")) else None
                    ic_val = r.get("innings_count")
                    ic = int(ic_val) if pd.notnull(ic_val) else 2

                    cond = conditions_map.get(mid, {})
                    is_dls = cond.get("is_dls", mid in DLS_MATCH_IDS)
                    is_super_over = mid in SUPER_OVER_MATCH_IDS or ic >= 4
                    is_no_result = cond.get("is_no_result", mid in NO_RESULT_MATCH_IDS or winner is None or ic < 2)
                    is_standard_20ov = cond.get("is_standard_20ov", not (is_dls or is_no_result))
                    condition_label = cond.get(
                        "condition_label",
                        "Standard 20-over match" if is_standard_20ov else ("Rain-interrupted / DLS" if is_dls else "Reduced overs (non-DLS)")
                    )

                    # Innings 1
                    inn1 = None
                    if inn1_raw:
                        runs1 = clean_num(inn1_raw.get("total_runs"))
                        wkts1 = clean_num(inn1_raw.get("total_wickets"))
                        ov1 = clean_num(inn1_raw.get("overs_completed"))
                        team1 = str(inn1_raw.get("batting_team", r.get("team1", "")))
                        is_full1 = bool(not is_dls and (ov1 is not None and ov1 >= 19.1 or wkts1 == 10))
                        inn1 = {
                            "team": team1,
                            "runs": int(runs1) if runs1 is not None else None,
                            "wickets": int(wkts1) if wkts1 is not None else None,
                            "overs": ov1,
                            "is_all_out": wkts1 == 10,
                            "is_full_innings": is_full1,
                            "score_str": f"{int(runs1)}/{int(wkts1)} ({ov1:.1f} ov)" if runs1 is not None and wkts1 is not None and ov1 is not None else "N/A",
                        }

                    # Innings 2
                    inn2 = None
                    if inn2_raw:
                        runs2 = clean_num(inn2_raw.get("total_runs"))
                        wkts2 = clean_num(inn2_raw.get("total_wickets"))
                        ov2 = clean_num(inn2_raw.get("overs_completed"))
                        tgt2 = clean_num(inn2_raw.get("target"))
                        team2 = str(inn2_raw.get("batting_team", r.get("team2", "")))
                        target_reached = bool(runs2 is not None and tgt2 is not None and runs2 >= tgt2)
                        is_full2 = bool(not is_dls and is_full1 and (target_reached or wkts2 == 10 or (ov2 is not None and ov2 >= 19.1)))
                        inn2 = {
                            "team": team2,
                            "runs": int(runs2) if runs2 is not None else None,
                            "wickets": int(wkts2) if wkts2 is not None else None,
                            "overs": ov2,
                            "target": tgt2,
                            "is_target_reached": target_reached,
                            "is_all_out": wkts2 == 10,
                            "is_full_innings": is_full2,
                            "score_str": f"{int(runs2)}/{int(wkts2)} ({ov2:.1f} ov)" if runs2 is not None and wkts2 is not None and ov2 is not None else "N/A",
                        }

                    result_type = "no_result"
                    result_desc = "No result / Match abandoned"
                    margin_str = ""

                    w_runs = clean_num(r.get("win_by_runs"))
                    w_wkts = clean_num(r.get("win_by_wickets"))

                    if is_no_result:
                        result_type = "no_result"
                        result_desc = "No result / Match abandoned"
                    elif is_super_over:
                        result_type = "tie_super_over"
                        result_desc = f"{winner} won via Super Over" if winner else "Match tied"
                        margin_str = "Super Over"
                    elif winner:
                        if inn1 and winner == inn1["team"]:
                            result_type = "defend_win"
                            if w_runs:
                                result_desc = f"{winner} won by {int(w_runs)} runs"
                                margin_str = f"{int(w_runs)} runs"
                            else:
                                result_desc = f"{winner} won defending"
                                margin_str = "Defended"
                        elif inn2 and winner == inn2["team"]:
                            result_type = "chase_win"
                            if w_wkts:
                                result_desc = f"{winner} won by {int(w_wkts)} wkts"
                                margin_str = f"{int(w_wkts)} wkts"
                            else:
                                result_desc = f"{winner} won chasing"
                                margin_str = "Chased"
                        else:
                            result_type = "chase_win" if w_wkts else "defend_win"
                            result_desc = f"{winner} won"

                    if is_dls and not is_no_result:
                        result_desc += " (DLS method)"

                    all_records.append({
                        "match_id": mid,
                        "competition": "ipl",
                        "competition_name": "Indian Premier League",
                        "season": str(r.get("season", "")),
                        "date": formatted_date,
                        "year": yr,
                        "venue_raw": raw_venue,
                        "venue": canon_venue,
                        "city": v_def["city"],
                        "country": v_def["country"],
                        "team1": str(r.get("team1", "")),
                        "team2": str(r.get("team2", "")),
                        "winner": winner,
                        "result_type": result_type,
                        "result_description": result_desc,
                        "margin": margin_str,
                        "is_dls": is_dls,
                        "is_super_over": is_super_over,
                        "is_no_result": is_no_result,
                        "is_standard_20ov": is_standard_20ov,
                        "condition_label": condition_label,
                        "innings1": inn1,
                        "innings2": inn2,
                    })

            # Helper for contributions-backed competitions (T20I and SA20)
            def _process_contrib_competition(comp_code: str, comp_name: str, def_year: int, def_country: str):
                data_service._ensure_loaded(comp_code)
                c_df = data_service.get_contributions_df(comp_code)
                m_df = data_service.get_matches_df(comp_code)

                inn_dict = {}
                if c_df is not None and not c_df.empty:
                    cols = ["match_id", "innings", "team", "final_team_score", "dismissal_status", "exit_over", "target"]
                    avail_cols = [c for c in cols if c in c_df.columns]
                    for r in c_df[avail_cols].to_dict("records"):
                        mid = str(r["match_id"])
                        if mid not in inn_dict:
                            inn_dict[mid] = {"inn1": None, "inn2": None}
                        inn = r.get("innings")
                        k = "inn1" if inn == 1 else ("inn2" if inn == 2 else None)
                        if not k:
                            continue
                        is_out = 1 if r.get("dismissal_status") == "out" else 0
                        ov = r.get("exit_over")
                        ov_val = clean_num(ov, 1)
                        curr = inn_dict[mid][k]
                        if curr is None:
                            runs_val = clean_num(r.get("final_team_score"))
                            tgt_val = clean_num(r.get("target")) if "target" in r else None
                            inn_dict[mid][k] = {
                                "team": str(r.get("team", "")),
                                "runs": int(runs_val) if runs_val is not None else None,
                                "wickets": is_out,
                                "overs": ov_val,
                                "target": tgt_val,
                            }
                        else:
                            curr["wickets"] += is_out
                            if ov_val is not None:
                                if curr["overs"] is None or ov_val > curr["overs"]:
                                    curr["overs"] = ov_val
                    for mid, info in inn_dict.items():
                        for k in ("inn1", "inn2"):
                            if info[k] is not None:
                                info[k]["is_all_out"] = (info[k]["wickets"] == 10)

                if m_df is not None and not m_df.empty:
                    for r in m_df.to_dict("records"):
                        mid = str(r["match_id"])
                        raw_venue = str(r.get("venue", "")).strip()
                        canon_venue = raw_to_canon.get(raw_venue, raw_venue)
                        v_def = CANONICAL_VENUE_DEFINITIONS.get(canon_venue, {
                            "canonical_name": canon_venue,
                            "city": str(r.get("city", "Unknown")),
                            "country": def_country,
                        })

                        d_str = str(r.get("date", ""))
                        if len(d_str) >= 10 and d_str[4] == "-" and d_str[7] == "-":
                            yr = int(d_str[:4])
                            formatted_date = d_str[:10]
                        else:
                            try:
                                dt = pd.to_datetime(d_str)
                                yr = int(dt.year)
                                formatted_date = dt.strftime("%Y-%m-%d")
                            except Exception:
                                yr = def_year
                                formatted_date = d_str

                        inn_info = inn_dict.get(mid, {})
                        inn1_raw = inn_info.get("inn1")
                        inn2_raw = inn_info.get("inn2")

                        winner = str(r.get("winner")) if pd.notnull(r.get("winner")) else None
                        ic_val = r.get("innings_count")
                        ic = int(ic_val) if pd.notnull(ic_val) else 2

                        cond = conditions_map.get(mid, {})
                        is_dls = cond.get("is_dls", mid in DLS_MATCH_IDS)
                        is_super_over = mid in SUPER_OVER_MATCH_IDS or ic >= 4 or mid == "1494261"
                        is_no_result = cond.get("is_no_result", mid in NO_RESULT_MATCH_IDS or winner is None or ic < 2)
                        is_standard_20ov = cond.get("is_standard_20ov", not (is_dls or is_no_result))
                        condition_label = cond.get(
                            "condition_label",
                            "Standard 20-over match" if is_standard_20ov else ("Rain-interrupted / DLS" if is_dls else "Reduced overs (non-DLS)")
                        )

                        inn1 = None
                        if inn1_raw:
                            runs1 = inn1_raw["runs"]
                            wkts1 = inn1_raw["wickets"]
                            ov1 = inn1_raw["overs"]
                            is_full1 = bool(not is_dls and (ov1 is not None and ov1 >= 19.1 or wkts1 == 10))
                            inn1 = {
                                "team": inn1_raw["team"],
                                "runs": runs1,
                                "wickets": wkts1,
                                "overs": ov1,
                                "is_all_out": wkts1 == 10,
                                "is_full_innings": is_full1,
                                "score_str": f"{runs1}/{wkts1} ({ov1:.1f} ov)" if runs1 is not None and ov1 is not None else "N/A",
                            }

                        inn2 = None
                        if inn2_raw:
                            runs2 = inn2_raw["runs"]
                            wkts2 = inn2_raw["wickets"]
                            ov2 = inn2_raw["overs"]
                            tgt2 = inn2_raw.get("target")
                            target_reached = bool(runs2 is not None and tgt2 is not None and runs2 >= tgt2)
                            is_full2 = bool(not is_dls and is_full1 and (target_reached or wkts2 == 10 or (ov2 is not None and ov2 >= 19.1)))
                            inn2 = {
                                "team": inn2_raw["team"],
                                "runs": runs2,
                                "wickets": wkts2,
                                "overs": ov2,
                                "target": tgt2,
                                "is_target_reached": target_reached,
                                "is_all_out": wkts2 == 10,
                                "is_full_innings": is_full2,
                                "score_str": f"{runs2}/{wkts2} ({ov2:.1f} ov)" if runs2 is not None and ov2 is not None else "N/A",
                            }

                        result_type = "no_result"
                        result_desc = "No result / Match abandoned"
                        margin_str = ""

                        w_runs = clean_num(r.get("win_by_runs"))
                        w_wkts = clean_num(r.get("win_by_wickets"))

                        if is_no_result:
                            result_type = "no_result"
                            result_desc = "No result / Match abandoned"
                        elif is_super_over:
                            result_type = "tie_super_over"
                            result_desc = f"{winner} won via Super Over" if winner else "Match tied"
                            margin_str = "Super Over"
                        elif winner:
                            if inn1 and winner == inn1["team"]:
                                result_type = "defend_win"
                                if w_runs:
                                    result_desc = f"{winner} won by {int(w_runs)} runs"
                                    margin_str = f"{int(w_runs)} runs"
                                else:
                                    result_desc = f"{winner} won defending"
                                    margin_str = "Defended"
                            elif inn2 and winner == inn2["team"]:
                                result_type = "chase_win"
                                if w_wkts:
                                    result_desc = f"{winner} won by {int(w_wkts)} wkts"
                                    margin_str = f"{int(w_wkts)} wkts"
                                else:
                                    result_desc = f"{winner} won chasing"
                                    margin_str = "Chased"
                            else:
                                result_type = "chase_win" if w_wkts else "defend_win"
                                result_desc = f"{winner} won"

                        if is_dls and not is_no_result:
                            result_desc += " (DLS method)"

                        all_records.append({
                            "match_id": mid,
                            "competition": comp_code,
                            "competition_name": comp_name,
                            "season": str(r.get("season", "")),
                            "date": formatted_date,
                            "year": yr,
                            "venue_raw": raw_venue,
                            "venue": canon_venue,
                            "city": v_def["city"],
                            "country": v_def["country"],
                            "team1": str(r.get("team1", "")),
                            "team2": str(r.get("team2", "")),
                            "winner": winner,
                            "result_type": result_type,
                            "result_description": result_desc,
                            "margin": margin_str,
                            "is_dls": is_dls,
                            "is_super_over": is_super_over,
                            "is_no_result": is_no_result,
                            "is_standard_20ov": is_standard_20ov,
                            "condition_label": condition_label,
                            "innings1": inn1,
                            "innings2": inn2,
                        })

            _process_contrib_competition("t20i", "Men's International T20", 2022, "Other / Unspecified")
            _process_contrib_competition("sa20", "SA20", 2023, "South Africa")

            self._matches_cache = all_records

    def get_countries_and_venues(
        self,
        competition: str = "combined",
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns dynamic list of countries and canonical venues populated from actual match records.
        """
        self._ensure_indexed()
        matches = self._matches_cache or []

        norm_comp = competition.strip().lower() if competition else "combined"
        if norm_comp in ("ipl", "t20i", "sa20"):
            matches = [m for m in matches if m["competition"] == norm_comp]

        # 1. Tally available countries
        country_counts: Dict[str, int] = {}
        for m in matches:
            c = m["country"]
            country_counts[c] = country_counts.get(c, 0) + 1

        sorted_countries = [
            {"name": c, "match_count": cnt}
            for c, cnt in sorted(country_counts.items(), key=lambda x: (-x[1], x[0]))
        ]

        # 2. Filter by country if specified
        venue_matches = matches
        if country and country.strip().lower() != "all":
            c_norm = country.strip().lower()
            venue_matches = [m for m in venue_matches if m["country"].lower() == c_norm]

        # 3. Tally venues
        venue_stats: Dict[str, Dict[str, Any]] = {}
        for m in venue_matches:
            v_name = m["venue"]
            if v_name not in venue_stats:
                venue_stats[v_name] = {
                    "id": v_name,
                    "name": v_name,
                    "city": m["city"],
                    "country": m["country"],
                    "total_matches": 0,
                    "ipl_matches": 0,
                    "t20i_matches": 0,
                    "sa20_matches": 0,
                    "earliest_date": m["date"],
                    "latest_date": m["date"],
                }
            st = venue_stats[v_name]
            st["total_matches"] += 1
            if m["competition"] == "ipl":
                st["ipl_matches"] += 1
            elif m["competition"] == "sa20":
                st["sa20_matches"] += 1
            else:
                st["t20i_matches"] += 1

            if m["date"] < st["earliest_date"]:
                st["earliest_date"] = m["date"]
            if m["date"] > st["latest_date"]:
                st["latest_date"] = m["date"]

        # Sort venues by total matches descending
        sorted_venues = sorted(venue_stats.values(), key=lambda x: (-x["total_matches"], x["name"]))

        # Identify recommended default venue
        default_venue = sorted_venues[0]["id"] if sorted_venues else "Wankhede Stadium, Mumbai"

        return {
            "competition": norm_comp,
            "selected_country": country or "All",
            "countries": sorted_countries,
            "venues": sorted_venues,
            "total_venues": len(sorted_venues),
            "default_venue": default_venue,
        }

    def get_ground_analysis(
        self,
        venue_id: str,
        competition: str = "combined",
        period: str = "rolling_5yr",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates venue scoring profile, chase vs defend rates, winning benchmarks,
        and season trends for the selected venue and scope.
        """
        self._ensure_indexed()
        all_matches = self._matches_cache or []

        # Resolve venue_id to canonical venue
        vid_norm = urllib.parse.unquote_plus(venue_id).replace("+", " ").strip()
        canon_name = RAW_TO_CANONICAL.get(vid_norm, vid_norm)

        # Match all occurrences for this canonical venue
        venue_all_matches = [m for m in all_matches if m["venue"].lower() == canon_name.lower()]
        if not venue_all_matches:
            # Fallback search by partial string
            venue_all_matches = [m for m in all_matches if vid_norm.lower() in m["venue"].lower() or vid_norm.lower() in m["venue_raw"].lower()]
            if not venue_all_matches:
                return None
            canon_name = venue_all_matches[0]["venue"]

        # Venue Metadata
        v_meta = CANONICAL_VENUE_DEFINITIONS.get(canon_name, {
            "canonical_name": canon_name,
            "city": venue_all_matches[0]["city"],
            "country": venue_all_matches[0]["country"],
            "aliases": [canon_name],
        })

        # Filter by Competition
        norm_comp = competition.strip().lower() if competition else "combined"
        comp_matches = venue_all_matches
        if norm_comp in ("ipl", "t20i", "sa20"):
            comp_matches = [m for m in venue_all_matches if m["competition"] == norm_comp]

        # Dataset absolute span for this venue
        if comp_matches:
            dates = [m["date"] for m in comp_matches]
            dataset_earliest = min(dates)
            dataset_latest = max(dates)
            total_all_time = len(comp_matches)
        else:
            dataset_earliest = "N/A"
            dataset_latest = "N/A"
            total_all_time = 0

        # Calculate Rolling 5-Year Window ending today
        today = datetime.date.today()
        try:
            five_years_ago = today.replace(year=today.year - 5)
        except ValueError:
            # Handle leap year Feb 29
            five_years_ago = today.replace(year=today.year - 5, day=28)

        norm_period = period.strip().lower() if period else "rolling_5yr"
        period_label = "Rolling 5-Year Window"
        eff_start_date = five_years_ago.strftime("%Y-%m-%d")
        eff_end_date = today.strftime("%Y-%m-%d")

        if norm_period == "all_time":
            period_label = "All Time History"
            eff_start_date = dataset_earliest
            eff_end_date = dataset_latest
        elif norm_period == "rolling_3yr":
            period_label = "Rolling 3-Year Window"
            eff_start_date = today.replace(year=today.year - 3).strftime("%Y-%m-%d")
            eff_end_date = today.strftime("%Y-%m-%d")
        elif start_date and end_date:
            period_label = f"Custom Period ({start_date} to {end_date})"
            eff_start_date = start_date
            eff_end_date = end_date
        else:
            period_label = f"Rolling 5-Year Window ({eff_start_date} to {eff_end_date})"

        # Apply Period Filter
        if norm_period != "all_time" and eff_start_date and eff_end_date:
            filtered_matches = [
                m for m in comp_matches if eff_start_date <= m["date"] <= eff_end_date
            ]
        else:
            filtered_matches = comp_matches

        # Sort filtered matches by date descending (newest first)
        filtered_matches.sort(key=lambda x: x["date"], reverse=True)
        total_in_period = len(filtered_matches)

        # -------------------------------------------------------------
        # 1. SCORING PROFILE (1st & 2nd Innings)
        # -------------------------------------------------------------
        # Eligibility: Completed 20-over innings or all-out; rain/DLS shortened innings excluded
        inn1_eligible = [
            m for m in filtered_matches
            if m["innings1"] and m["innings1"]["runs"] is not None and m["innings1"]["is_full_innings"]
        ]
        inn2_eligible = [
            m for m in filtered_matches
            if m["innings2"] and m["innings2"]["runs"] is not None and m["innings2"]["is_full_innings"]
        ]

        def _calc_inn_profile(eligible_list, inn_key):
            if not eligible_list:
                return {
                    "avg_score": None,
                    "median_score": None,
                    "highest": None,
                    "lowest": None,
                    "sample_count": 0,
                    "eligibility_note": "No eligible full 20-over innings in selected period.",
                }

            runs_list = [m[inn_key]["runs"] for m in eligible_list]
            avg_val = round(float(np.mean(runs_list)), 1)
            med_val = round(float(np.median(runs_list)), 1)

            # Max
            max_r = max(runs_list)
            max_m = next(m for m in eligible_list if m[inn_key]["runs"] == max_r)
            highest_obj = {
                "runs": max_r,
                "score_str": max_m[inn_key]["score_str"],
                "team": max_m[inn_key]["team"],
                "opponent": max_m["team2"] if max_m[inn_key]["team"] == max_m["team1"] else max_m["team1"],
                "match_id": max_m["match_id"],
                "date": max_m["date"],
                "competition": max_m["competition_name"],
                "result_description": max_m["result_description"],
            }

            # Min
            min_r = min(runs_list)
            min_m = next(m for m in eligible_list if m[inn_key]["runs"] == min_r)
            lowest_obj = {
                "runs": min_r,
                "score_str": min_m[inn_key]["score_str"],
                "team": min_m[inn_key]["team"],
                "opponent": min_m["team2"] if min_m[inn_key]["team"] == min_m["team1"] else min_m["team1"],
                "match_id": min_m["match_id"],
                "date": min_m["date"],
                "competition": min_m["competition_name"],
                "result_description": min_m["result_description"],
            }

            return {
                "avg_score": avg_val,
                "median_score": med_val,
                "highest": highest_obj,
                "lowest": lowest_obj,
                "sample_count": len(eligible_list),
                "eligibility_note": (
                    "Completed 20-over innings or all-out in regulation matches; rain/DLS shortened innings excluded."
                    if inn_key == "innings1"
                    else "Completed chases (target reached or regulation all-out/20 ov); rain-interrupted chases excluded."
                ),
            }

        scoring_profile = {
            "first_innings": _calc_inn_profile(inn1_eligible, "innings1"),
            "second_innings": _calc_inn_profile(inn2_eligible, "innings2"),
        }

        # -------------------------------------------------------------
        # 2. CHASE VS DEFEND OUTCOMES
        # -------------------------------------------------------------
        defend_wins = sum(1 for m in filtered_matches if m["result_type"] == "defend_win")
        chase_wins = sum(1 for m in filtered_matches if m["result_type"] == "chase_win")
        ties = sum(1 for m in filtered_matches if m["result_type"] == "tie_super_over")
        no_results = sum(1 for m in filtered_matches if m["result_type"] == "no_result")

        decided_matches = defend_wins + chase_wins
        defend_pct = round((defend_wins / decided_matches) * 100.0, 1) if decided_matches > 0 else None
        chase_pct = round((chase_wins / decided_matches) * 100.0, 1) if decided_matches > 0 else None

        chase_vs_defend = {
            "defend_wins": defend_wins,
            "chase_wins": chase_wins,
            "decided_matches": decided_matches,
            "defend_pct": defend_pct,
            "chase_pct": chase_pct,
            "ties_super_overs": ties,
            "no_results_abandoned": no_results,
            "total_matches": total_in_period,
            "calculation_note": (
                "Percentages calculated strictly from decided matches (defend wins + chase wins). "
                "Ties, super overs, and no-results are recorded separately and excluded from the win-percentage denominator."
            ),
        }

        # -------------------------------------------------------------
        # 3. HISTORICAL WINNING SCORES & BENCHMARKS
        # -------------------------------------------------------------
        # Lowest Successful Defense: lowest innings 1 total in completed matches won defending
        defend_matches = [
            m for m in filtered_matches
            if m["result_type"] == "defend_win" and m["is_standard_20ov"] and m["innings1"] and m["innings1"]["runs"] is not None and m["innings1"]["is_full_innings"]
        ]
        lowest_defense = None
        if defend_matches:
            min_def = min(defend_matches, key=lambda m: m["innings1"]["runs"])
            lowest_defense = {
                "first_innings_score": min_def["innings1"]["runs"],
                "score_str": min_def["innings1"]["score_str"],
                "defending_team": min_def["innings1"]["team"],
                "chasing_team": min_def["innings2"]["team"] if min_def["innings2"] else min_def["team2"],
                "chasing_score_str": min_def["innings2"]["score_str"] if min_def["innings2"] else "N/A",
                "match_id": min_def["match_id"],
                "date": min_def["date"],
                "competition": min_def["competition_name"],
                "result_description": min_def["result_description"],
            }

        # Lowest Successful Chase: lowest second-innings target successfully chased in full match
        chase_matches = [
            m for m in filtered_matches
            if m["result_type"] == "chase_win" and m["is_standard_20ov"] and m["innings2"] and m["innings2"]["runs"] is not None and m["innings2"]["is_full_innings"]
        ]
        lowest_chase = None
        highest_chase = None
        if chase_matches:
            # Lowest chase score
            min_ch = min(chase_matches, key=lambda m: m["innings2"]["runs"])
            lowest_chase = {
                "chase_score": min_ch["innings2"]["runs"],
                "score_str": min_ch["innings2"]["score_str"],
                "chasing_team": min_ch["innings2"]["team"],
                "target_set": min_ch["innings1"]["runs"] if min_ch["innings1"] else None,
                "first_innings_score_str": min_ch["innings1"]["score_str"] if min_ch["innings1"] else "N/A",
                "match_id": min_ch["match_id"],
                "date": min_ch["date"],
                "competition": min_ch["competition_name"],
                "result_description": min_ch["result_description"],
            }
            # Highest chase score
            max_ch = max(chase_matches, key=lambda m: m["innings2"]["runs"])
            highest_chase = {
                "chase_score": max_ch["innings2"]["runs"],
                "score_str": max_ch["innings2"]["score_str"],
                "chasing_team": max_ch["innings2"]["team"],
                "target_set": max_ch["innings1"]["runs"] if max_ch["innings1"] else None,
                "first_innings_score_str": max_ch["innings1"]["score_str"] if max_ch["innings1"] else "N/A",
                "match_id": max_ch["match_id"],
                "date": max_ch["date"],
                "competition": max_ch["competition_name"],
                "result_description": max_ch["result_description"],
            }

        # Typical Winning Score (Median winning total)
        winning_scores_all = []
        winning_scores_defend = []
        winning_scores_chase = []
        for m in filtered_matches:
            if m["is_dls"]:
                continue
            if m["result_type"] == "defend_win" and m["innings1"] and m["innings1"]["runs"] is not None:
                winning_scores_all.append(m["innings1"]["runs"])
                winning_scores_defend.append(m["innings1"]["runs"])
            elif m["result_type"] == "chase_win" and m["innings2"] and m["innings2"]["runs"] is not None:
                winning_scores_all.append(m["innings2"]["runs"])
                winning_scores_chase.append(m["innings2"]["runs"])

        typical_winning_score = {
            "overall_median": round(float(np.median(winning_scores_all)), 1) if winning_scores_all else None,
            "defending_median": round(float(np.median(winning_scores_defend)), 1) if winning_scores_defend else None,
            "chasing_median": round(float(np.median(winning_scores_chase)), 1) if winning_scores_chase else None,
            "sample_count": len(winning_scores_all),
        }

        benchmarks = {
            "lowest_successful_defense": lowest_defense,
            "lowest_successful_chase": lowest_chase,
            "highest_successful_chase": highest_chase,
            "typical_winning_score": typical_winning_score,
            "sample_adequate": decided_matches >= 3,
            "warning": None if decided_matches >= 3 else "Limited match sample size (<3 decided matches). Historical benchmarks may be volatile.",
            "note": "Historical observations from full regulation matches; excludes rain-shortened/DLS adjustments.",
        }

        # -------------------------------------------------------------
        # 4. SEASON AND YEAR TRENDS
        # -------------------------------------------------------------
        # Group by year
        year_groups: Dict[int, List[Dict[str, Any]]] = {}
        for m in filtered_matches:
            yr = m["year"]
            year_groups.setdefault(yr, []).append(m)

        year_trends = []
        for yr in sorted(year_groups.keys()):
            ym_list = year_groups[yr]
            y_tot = len(ym_list)
            y_def = sum(1 for m in ym_list if m["result_type"] == "defend_win")
            y_ch = sum(1 for m in ym_list if m["result_type"] == "chase_win")
            y_dec = y_def + y_ch
            y_def_pct = round((y_def / y_dec) * 100.0, 1) if y_dec > 0 else None
            y_ch_pct = round((y_ch / y_dec) * 100.0, 1) if y_dec > 0 else None

            # Average innings scores
            y_inn1 = [m["innings1"]["runs"] for m in ym_list if m["innings1"] and m["innings1"]["is_full_innings"] and m["innings1"]["runs"] is not None]
            y_inn2 = [m["innings2"]["runs"] for m in ym_list if m["innings2"] and m["innings2"]["is_full_innings"] and m["innings2"]["runs"] is not None]

            y_avg1 = round(float(np.mean(y_inn1)), 1) if y_inn1 else None
            y_avg2 = round(float(np.mean(y_inn2)), 1) if y_inn2 else None

            year_trends.append({
                "year": yr,
                "matches": y_tot,
                "decided_matches": y_dec,
                "avg_first_innings": y_avg1,
                "avg_second_innings": y_avg2,
                "defend_wins": y_def,
                "chase_wins": y_ch,
                "defend_pct": y_def_pct,
                "chase_pct": y_ch_pct,
            })

        # -------------------------------------------------------------
        # 5. RECENT MATCH HISTORY LIST
        # -------------------------------------------------------------
        recent_matches = []
        for m in filtered_matches[:50]:  # Up to 50 recent matches in period
            raw_cond = m.get("condition_label", "")
            if m.get("is_dls") or "DLS" in raw_cond or "Rain" in raw_cond or "rain" in raw_cond:
                c_label = "DLS / Rain-shortened"
            elif "Reduced" in raw_cond or "reduced" in raw_cond or (not m.get("is_standard_20ov", True) and not m.get("is_no_result")):
                c_label = "Reduced Overs"
            elif "Unknown" in raw_cond or "unknown" in raw_cond:
                c_label = "Unknown Conditions"
            elif m.get("is_standard_20ov", True):
                c_label = "Standard 20-over match"
            else:
                c_label = raw_cond or "Standard 20-over match"

            recent_matches.append({
                "match_id": m["match_id"],
                "date": m["date"],
                "competition": m.get("competition_name") or ("IPL" if m["competition"] == "ipl" else ("SA20" if m["competition"] == "sa20" else "International T20I")),
                "competition_code": m["competition"],
                "team1": m["team1"],
                "team2": m["team2"],
                "innings1_team": m["innings1"]["team"] if m["innings1"] else m["team1"],
                "innings1_score": m["innings1"]["score_str"] if m["innings1"] else "N/A",
                "innings1_runs": m["innings1"]["runs"] if m["innings1"] else None,
                "innings2_team": m["innings2"]["team"] if m["innings2"] else m["team2"],
                "innings2_score": m["innings2"]["score_str"] if m["innings2"] else "N/A",
                "innings2_runs": m["innings2"]["runs"] if m["innings2"] else None,
                "winner": m["winner"],
                "result_type": m["result_type"],
                "result_description": m["result_description"],
                "margin": m["margin"],
                "is_dls": m["is_dls"],
                "is_super_over": m["is_super_over"],
                "is_no_result": m["is_no_result"],
                "is_standard_20ov": m.get("is_standard_20ov", True),
                "condition_label": c_label,
                "match_url": f"/match/{m['match_id']}",
            })

        # -------------------------------------------------------------
        # 6. PHASE-WISE SCORING PROFILE (Powerplay, Middle, Death)
        # -------------------------------------------------------------
        self._ensure_phases_loaded()
        phases_map = self._phases_data.get("phases", {})

        standard_matches = [m for m in filtered_matches if m.get("is_standard_20ov", True)]
        excluded_matches = [m for m in filtered_matches if not m.get("is_standard_20ov", True)]
        unknown_matches = sum(1 for m in filtered_matches if m.get("condition_label") == "Unknown conditions")

        scope_summary = {
            "total_matches_in_period": total_in_period,
            "eligible_standard_matches": len(standard_matches),
            "excluded_matches": len(excluded_matches),
            "unknown_matches": unknown_matches,
            "disclosure_text": (
                f"Phase statistics include only fully completed phases from eligible standard 20-over matches ({len(standard_matches)} matches available). "
                f"An additional {len(excluded_matches)} rain-interrupted or reduced-overs matches were excluded."
            ),
            "eligibility_rule": "Phase statistics include only fully completed phases from eligible standard 20-over matches.",
        }

        def _calc_phase_metrics(phase_id: str, innings_filter: Optional[int] = None):
            eligible_records = []
            inns_to_check = [1, 2] if innings_filter is None else [innings_filter]

            for m in standard_matches:
                mid = str(m["match_id"])
                match_phases = phases_map.get(mid, {})
                for inn_num in inns_to_check:
                    inn_key = str(inn_num)
                    inn_d = match_phases.get(inn_key)
                    if inn_d is None:
                        alt_d = match_phases.get(f"innings{inn_num}")
                        if isinstance(alt_d, dict):
                            inn_d = alt_d.get("phases", alt_d)
                    if not isinstance(inn_d, dict):
                        continue

                    ph_data = inn_d.get(phase_id)
                    if not ph_data:
                        continue

                    is_played = ph_data.get("played")
                    if is_played is None:
                        is_played = ph_data.get("legal_balls", 0) > 0 or ph_data.get("runs", 0) > 0
                    if not is_played:
                        continue

                    # Full-phase eligibility check:
                    # Only include a phase when the batting team had the opportunity to complete the entire phase:
                    # - Powerplay: overs 1–6 (overs 7+ played or 36 legal balls)
                    # - Middle Overs: overs 7–15 (powerplay complete AND (overs 16+ played or 54 legal balls))
                    # - Death Overs: overs 16–20 (powerplay complete, middle complete, AND all 5 scheduled overs completed: 30 legal balls)
                    is_comp = ph_data.get("complete")
                    if is_comp is None:
                        pp_d = inn_d.get("powerplay", {})
                        mid_d = inn_d.get("middle", {})
                        dth_d = inn_d.get("death", {})
                        is_std = m.get("is_standard_20ov", False)
                        pp_played = pp_d.get("played", pp_d.get("legal_balls", 0) > 0)
                        mid_played = mid_d.get("played", mid_d.get("legal_balls", 0) > 0)
                        dth_played = dth_d.get("played", dth_d.get("legal_balls", 0) > 0)
                        pp_ok = bool(is_std and pp_played and (mid_played or pp_d.get("legal_balls", 0) >= 36))
                        mid_ok = bool(is_std and pp_ok and mid_played and (dth_played or mid_d.get("legal_balls", 0) >= 54))
                        dth_ok = bool(is_std and pp_ok and mid_ok and dth_played and (dth_d.get("legal_balls", 0) >= 30))
                        if phase_id == "powerplay":
                            is_comp = pp_ok
                        elif phase_id == "middle":
                            is_comp = mid_ok
                        elif phase_id == "death":
                            is_comp = dth_ok
                        else:
                            is_comp = False

                    if not is_comp:
                        continue

                    inn_info = m["innings1"] if inn_num == 1 else m["innings2"]
                    if not inn_info:
                        continue

                    team = inn_info["team"]
                    opp = m["team2"] if team == m["team1"] else m["team1"]
                    r = ph_data["runs"]
                    w = ph_data["wickets"]
                    lb = ph_data["legal_balls"]
                    d = ph_data.get("dot_balls", 0)
                    b = ph_data.get("boundary_balls", 0)

                    ov_str = f"{lb // 6}.{lb % 6} ov"
                    score_str = f"{r}/{w} ({ov_str})"

                    eligible_records.append({
                        "match_id": m["match_id"],
                        "date": m["date"],
                        "year": m["year"],
                        "competition": m.get("competition_name") or ("IPL" if m["competition"] == "ipl" else ("SA20" if m["competition"] == "sa20" else "International T20I")),
                        "competition_name": m["competition_name"],
                        "team": team,
                        "opponent": opp,
                        "result_description": m["result_description"],
                        "runs": r,
                        "wickets": w,
                        "legal_balls": lb,
                        "dot_balls": d,
                        "boundary_balls": b,
                        "score_str": score_str,
                        "ov_str": ov_str,
                    })

            ph_title = "Powerplay" if phase_id == "powerplay" else ("Middle Overs" if phase_id == "middle" else "Death Overs")
            ov_range = "Overs 1–6" if phase_id == "powerplay" else ("Overs 7–15" if phase_id == "middle" else "Overs 16–20")

            if not eligible_records:
                return {
                    "phase_id": phase_id,
                    "phase_name": ph_title,
                    "overs_range": ov_range,
                    "avg_runs": None,
                    "median_runs": None,
                    "highest": None,
                    "lowest": None,
                    "avg_wickets": None,
                    "run_rate": None,
                    "dot_percentage": None,
                    "boundary_percentage": None,
                    "sample_innings": 0,
                    "sample_matches": 0,
                }

            runs_list = [rec["runs"] for rec in eligible_records]
            wkts_list = [rec["wickets"] for rec in eligible_records]
            tot_runs = sum(runs_list)
            tot_legal = sum(rec["legal_balls"] for rec in eligible_records)
            tot_dots = sum(rec["dot_balls"] for rec in eligible_records)
            tot_bnd = sum(rec["boundary_balls"] for rec in eligible_records)

            avg_r = round(float(np.mean(runs_list)), 1)
            med_r = round(float(np.median(runs_list)), 1)
            avg_w = round(float(np.mean(wkts_list)), 2)
            rr = round((tot_runs / tot_legal) * 6, 2) if tot_legal > 0 else None
            dot_pct = round((tot_dots / tot_legal) * 100, 1) if tot_legal > 0 else None
            bnd_pct = round((tot_bnd / tot_legal) * 100, 1) if tot_legal > 0 else None

            high_rec = max(eligible_records, key=lambda x: (x["runs"], -x["wickets"], -x["legal_balls"]))
            highest_obj = {
                "runs": high_rec["runs"],
                "wickets": high_rec["wickets"],
                "legal_balls": high_rec["legal_balls"],
                "score_str": high_rec["score_str"],
                "overs_str": high_rec["ov_str"],
                "team": high_rec["team"],
                "opponent": high_rec["opponent"],
                "match_id": high_rec["match_id"],
                "date": high_rec["date"],
                "competition": high_rec["competition"],
                "result_description": high_rec["result_description"],
            }

            low_rec = min(eligible_records, key=lambda x: (x["runs"], -x["wickets"], x["legal_balls"]))
            lowest_obj = {
                "runs": low_rec["runs"],
                "wickets": low_rec["wickets"],
                "legal_balls": low_rec["legal_balls"],
                "score_str": low_rec["score_str"],
                "overs_str": low_rec["ov_str"],
                "team": low_rec["team"],
                "opponent": low_rec["opponent"],
                "match_id": low_rec["match_id"],
                "date": low_rec["date"],
                "competition": low_rec["competition"],
                "result_description": low_rec["result_description"],
            }

            unique_matches = len(set(rec["match_id"] for rec in eligible_records))

            return {
                "phase_id": phase_id,
                "phase_name": ph_title,
                "overs_range": ov_range,
                "avg_runs": avg_r,
                "median_runs": med_r,
                "highest": highest_obj,
                "lowest": lowest_obj,
                "avg_wickets": avg_w,
                "run_rate": rr,
                "dot_percentage": dot_pct,
                "boundary_percentage": bnd_pct,
                "sample_innings": len(eligible_records),
                "sample_matches": unique_matches,
            }

        phase_profiles = {
            "first_innings": {
                "powerplay": _calc_phase_metrics("powerplay", 1),
                "middle": _calc_phase_metrics("middle", 1),
                "death": _calc_phase_metrics("death", 1),
            },
            "second_innings": {
                "powerplay": _calc_phase_metrics("powerplay", 2),
                "middle": _calc_phase_metrics("middle", 2),
                "death": _calc_phase_metrics("death", 2),
            },
            "combined": {
                "powerplay": _calc_phase_metrics("powerplay", None),
                "middle": _calc_phase_metrics("middle", None),
                "death": _calc_phase_metrics("death", None),
            },
        }

        comparison_chart = []
        for ph in ("powerplay", "middle", "death"):
            p1 = phase_profiles["first_innings"][ph]
            p2 = phase_profiles["second_innings"][ph]
            pc = phase_profiles["combined"][ph]
            comparison_chart.append({
                "phase_id": ph,
                "phase_name": f"{p1['phase_name']} ({p1['overs_range']})",
                "first_innings_avg_runs": p1["avg_runs"],
                "second_innings_avg_runs": p2["avg_runs"],
                "combined_avg_runs": pc["avg_runs"],
                "first_innings_run_rate": p1["run_rate"],
                "second_innings_run_rate": p2["run_rate"],
                "combined_run_rate": pc["run_rate"],
                "first_innings_sample": p1["sample_innings"],
                "second_innings_sample": p2["sample_innings"],
                "combined_sample": pc["sample_innings"],
                "first_innings_matches": p1["sample_matches"],
                "second_innings_matches": p2["sample_matches"],
                "combined_matches": pc["sample_matches"],
            })

        # Progression Insights
        pp_rr = phase_profiles["combined"]["powerplay"]["run_rate"]
        mid_rr = phase_profiles["combined"]["middle"]["run_rate"]
        dth_rr = phase_profiles["combined"]["death"]["run_rate"]

        pp_w = phase_profiles["combined"]["powerplay"]["avg_wickets"]
        mid_w = phase_profiles["combined"]["middle"]["avg_wickets"]
        dth_w = phase_profiles["combined"]["death"]["avg_wickets"]

        sample_ok = len(standard_matches) >= 3

        if sample_ok and pp_rr is not None and mid_rr is not None and dth_rr is not None:
            pp_mid_diff = round(mid_rr - pp_rr, 2)
            mid_dth_diff = round(dth_rr - mid_rr, 2)

            if mid_dth_diff > 0.75:
                rate_insight = f"Scoring rate tends to increase significantly in the death overs ({dth_rr} rpo vs {mid_rr} rpo in middle overs, a +{mid_dth_diff} rpo lift)."
            elif mid_dth_diff > 0.2:
                rate_insight = f"Scoring rate shows moderate acceleration into the death overs ({dth_rr} rpo vs {mid_rr} rpo in middle overs)."
            elif mid_dth_diff < -0.5:
                rate_insight = f"Death overs scoring rate ({dth_rr} rpo) drops below middle overs ({mid_rr} rpo), pointing to late-innings containment or lower-order collapses."
            else:
                rate_insight = f"Scoring rate remains steady across middle ({mid_rr} rpo) and death overs ({dth_rr} rpo)."

            if pp_mid_diff < -0.3:
                pp_insight = f"Powerplay scoring ({pp_rr} rpo) is higher than middle overs ({mid_rr} rpo), reflecting early fielding restriction exploitation."
            elif pp_mid_diff > 0.3:
                pp_insight = f"Middle-overs scoring ({mid_rr} rpo) accelerates beyond the Powerplay ({pp_rr} rpo) as batters settle."
            else:
                pp_insight = f"Powerplay ({pp_rr} rpo) and middle-overs scoring ({mid_rr} rpo) remain closely matched."

            wicket_insight = (
                f"Wicket loss historically averages {pp_w} in the Powerplay, {mid_w} across the middle overs, "
                f"and {dth_w} in the death phase."
            )
            context_note = (
                "Observed historical scoring and wicket trends reflect tactical phase approaches, field restrictions, "
                "wickets in hand, and batting quality rather than pitch surface behavior alone."
            )
            progression_insights = {
                "powerplay_run_rate": pp_rr,
                "middle_run_rate": mid_rr,
                "death_run_rate": dth_rr,
                "pp_to_middle_diff": pp_mid_diff,
                "middle_to_death_diff": mid_dth_diff,
                "pp_avg_wickets": pp_w,
                "middle_avg_wickets": mid_w,
                "death_avg_wickets": dth_w,
                "rate_insight": f"{rate_insight} {pp_insight}",
                "wicket_insight": wicket_insight,
                "context_note": context_note,
                "is_reliable": True,
            }
        else:
            progression_insights = {
                "powerplay_run_rate": pp_rr,
                "middle_run_rate": mid_rr,
                "death_run_rate": dth_rr,
                "pp_to_middle_diff": None,
                "middle_to_death_diff": None,
                "pp_avg_wickets": pp_w,
                "middle_avg_wickets": mid_w,
                "death_avg_wickets": dth_w,
                "rate_insight": "Sample size is insufficient (<3 standard 20-over matches) to establish reliable scoring progression trends.",
                "wicket_insight": "Insufficient sample for reliable wicket progression.",
                "context_note": "A minimum of 3 standard 20-over matches is required for progression analysis.",
                "is_reliable": False,
            }

        # Phase year trends
        phase_year_groups: Dict[int, List[Dict[str, Any]]] = {}
        for m in standard_matches:
            phase_year_groups.setdefault(m["year"], []).append(m)

        phase_year_trends = []
        for yr in sorted(phase_year_groups.keys()):
            ym_list = phase_year_groups[yr]
            y_pp_runs = []
            y_pp_legal = []
            y_mid_runs = []
            y_mid_legal = []
            y_dth_runs = []
            y_dth_legal = []

            for m in ym_list:
                mid = str(m["match_id"])
                mph = phases_map.get(mid, {})
                for inn_k in ("1", "2"):
                    inn_d = mph.get(inn_k)
                    if inn_d is None:
                        alt_d = mph.get(f"innings{inn_k}")
                        if isinstance(alt_d, dict):
                            inn_d = alt_d.get("phases", alt_d)
                    if not isinstance(inn_d, dict):
                        continue

                    pp_d = inn_d.get("powerplay", {})
                    mid_d = inn_d.get("middle", {})
                    dth_d = inn_d.get("death", {})

                    is_std = m.get("is_standard_20ov", False)
                    pp_played = pp_d.get("played", pp_d.get("legal_balls", 0) > 0)
                    mid_played = mid_d.get("played", mid_d.get("legal_balls", 0) > 0)
                    dth_played = dth_d.get("played", dth_d.get("legal_balls", 0) > 0)

                    pp_ok = pp_d.get("complete") if pp_d.get("complete") is not None else bool(is_std and pp_played and (mid_played or pp_d.get("legal_balls", 0) >= 36))
                    mid_ok = mid_d.get("complete") if mid_d.get("complete") is not None else bool(is_std and pp_ok and mid_played and (dth_played or mid_d.get("legal_balls", 0) >= 54))
                    dth_ok = dth_d.get("complete") if dth_d.get("complete") is not None else bool(is_std and pp_ok and mid_ok and dth_played and (dth_d.get("legal_balls", 0) >= 30))

                    if pp_ok:
                        y_pp_runs.append(pp_d["runs"])
                        y_pp_legal.append(pp_d["legal_balls"])
                    if mid_ok:
                        y_mid_runs.append(mid_d["runs"])
                        y_mid_legal.append(mid_d["legal_balls"])
                    if dth_ok:
                        y_dth_runs.append(dth_d["runs"])
                        y_dth_legal.append(dth_d["legal_balls"])

            pp_l_sum = sum(y_pp_legal)
            mid_l_sum = sum(y_mid_legal)
            dth_l_sum = sum(y_dth_legal)

            phase_year_trends.append({
                "year": yr,
                "matches": len(ym_list),
                "powerplay_avg_runs": round(float(np.mean(y_pp_runs)), 1) if y_pp_runs else None,
                "powerplay_run_rate": round((sum(y_pp_runs) / pp_l_sum) * 6, 2) if pp_l_sum > 0 else None,
                "middle_avg_runs": round(float(np.mean(y_mid_runs)), 1) if y_mid_runs else None,
                "middle_run_rate": round((sum(y_mid_runs) / mid_l_sum) * 6, 2) if mid_l_sum > 0 else None,
                "death_avg_runs": round(float(np.mean(y_dth_runs)), 1) if y_dth_runs else None,
                "death_run_rate": round((sum(y_dth_runs) / dth_l_sum) * 6, 2) if dth_l_sum > 0 else None,
            })

        phase_analysis = {
            "scope_summary": scope_summary,
            "eligibility_note": "Phase statistics include only fully completed phases from eligible standard 20-over matches.",
            "first_innings": phase_profiles["first_innings"],
            "second_innings": phase_profiles["second_innings"],
            "combined": phase_profiles["combined"],
            "comparison_chart": comparison_chart,
            "progression_insights": progression_insights,
            "year_trends": phase_year_trends,
        }

        return {
            "venue_info": {
                "id": canon_name,
                "name": canon_name,
                "city": v_meta["city"],
                "country": v_meta["country"],
                "aliases": v_meta["aliases"],
            },
            "filters": {
                "competition": norm_comp,
                "period": norm_period,
                "period_label": period_label,
                "start_date": eff_start_date,
                "end_date": eff_end_date,
            },
            "summary": {
                "total_matches_in_period": total_in_period,
                "total_matches_all_time": total_all_time,
                "earliest_date_in_scope": min(m["date"] for m in filtered_matches) if filtered_matches else "N/A",
                "latest_date_in_scope": max(m["date"] for m in filtered_matches) if filtered_matches else "N/A",
                "dataset_earliest_date": dataset_earliest,
                "dataset_latest_date": dataset_latest,
                "data_coverage_notice": (
                    f"Selected period ({eff_start_date} to {eff_end_date}) contains {total_in_period} recorded matches. "
                    f"Historical dataset coverage at {canon_name} spans from {dataset_earliest} to {dataset_latest} ({total_all_time} total matches recorded in CricImpact). "
                    "Dataset coverage does not guarantee every historical match was played or recorded."
                ),
            },
            "scoring_profile": scoring_profile,
            "phase_analysis": phase_analysis,
            "chase_vs_defend": chase_vs_defend,
            "historical_winning_scores": benchmarks,
            "year_trends": year_trends,
            "recent_matches": recent_matches,
        }


# Singleton service instance
ground_service = GroundAnalysisService()
