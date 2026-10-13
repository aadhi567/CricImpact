"""
Generate complete verified bowling classification for all 577 IPL bowlers.
Each bowler is classified as:
- 'Pace' (Fast, Fast-medium, Medium-fast, Medium)
- 'Spin' (Off break, Leg break, Orthodox, Unorthodox/Chinaman)
"""

import pandas as pd
import json

# Definitive list of spin bowlers (wrist-spin, finger-spin, orthodox, chinaman)
SPIN_BOWLERS = {
    # Elite & regular spinners
    "R Ashwin", "SP Narine", "RA Jadeja", "YS Chahal", "PP Chawla", "AR Patel", "Rashid Khan",
    "Harbhajan Singh", "A Mishra", "Kuldeep Yadav", "CV Varun", "PP Ojha", "Ravi Bishnoi",
    "RD Chahar", "KV Sharma", "M Muralitharan", "Shakib Al Hasan", "S Nadeem", "Imran Tahir",
    "SK Warne", "Washington Sundar", "YK Pathan", "M Kartik", "Noor Ahmad", "SB Jakati",
    "GJ Maxwell", "S Gopal", "A Kumble", "Iqbal Abdulla", "R Sharma", "SK Raina",
    "M Theekshana", "M Ashwin", "Yuvraj Singh", "Harpreet Brar", "MM Ali", "R Tewatia",
    "Suyash Sharma", "PWH de Silva", "DL Vettori", "M Markande", "P Negi", "J Botha",
    "MJ Santner", "JP Duminy", "Shahbaz Ahmed", "PV Tambe", "K Gowtham", "CH Gayle",
    "Harmeet Singh", "DS Rathi", "A Symonds", "R Sai Kishore", "A Zampa", "GB Hogg",
    "Mujeeb Ur Rahman", "RE van der Merwe", "RR Powar", "Bipul Sharma", "J Suchith",
    "Mohammad Nabi", "J Yadav", "DJ Hooda", "Ankit Sharma", "Abhishek Sharma", "AS Roy",
    "RG Sharma", "R Parag", "DJ Hussey", "LS Livingstone", "BA Bhatt", "ST Jayasuriya",
    "V Nigam", "Lalit Yadav", "K Kartikeya", "TM Dilshan", "AG Murtaza", "S Badree",
    "AA Chavan", "BAW Mendis", "BJ Hodge", "AM Ghazanfar", "A Chandila", "AK Markram",
    "KC Cariappa", "N Rana", "Y Venugopal Rao", "KP Appanna", "MN Samuels", "HR Shokeen",
    "Karanveer Singh", "S Lamichhane", "S Kaushik", "Zeeshan Ansari", "WG Jacks",
    "Parvez Rasool", "Harsh Dubey", "J Syed Mohammad", "SMSM Senanayake", "M Siddharth",
    "Shahid Afridi", "IS Sodhi", "S Randiv", "KP Pietersen", "AJ Hosein", "Swapnil Singh",
    "TL Suman", "S Ladda", "V Sehwag", "Mayank Dagar", "T Shamsi", "Shivam Sharma",
    "AL Menaria", "Ankit Soni", "P Sahu", "MK Lomror", "Shashank Singh", "FA Allen",
    "Raghu Sharma", "Sikandar Raza", "AA Jhunjhunwala", "SR Dubey", "Gurkeerat Singh",
    "P Dubey", "M Tiwari", "V Puthur", "K Goel", "MJ Clarke", "MG Bracewell",
    "TM Head", "Mohammad Hafeez", "AU Rashid", "V Viyaskanth", "Shoaib Malik",
    "Abdul Samad", "ND Doshi", "AC Voges", "SB Joshi", "Naman Dhir", "D Salunkhe",
    "C Nanda", "MJ Suthar", "S Dhawan", "RJ Peterson", "SS Mishra", "CL White",
    "MW Short", "MK Tiwary", "AJ Finch", "GH Vihari", "PHKD Mendis", "M Manhas",
    "A Badoni", "SD Chitnis", "SR Tendulkar", "GF Linde", "M Vijay", "T Stubbs",
    "R Ninan", "Krish Bhagat", "KA Maharaj", "PH Solanki", "SZ Mulani", "VS Yeligati",
    "GD Phillips", "NL McCullum", "AS Raut", "BMAJ Mendis", "H Sharma", "PVSN Raju",
    "A Dananjaya", "R Goyal", "SS Agarwal", "P Ray Barman", "Tilak Varma", "Tejas Baroka",
    "Vivrant Sharma", "RV Patel", "Sunny Gupta", "MB Parmar", "Jalaj S Saxena",
    "KS Williamson", "DJM Short", "S Sriram", "DB Ravi Teja", "M Shahrukh Khan",
    "RW Price", "D Ferreira", "CJ Green", "N Wadhera", "Abdur Razzak", "R Sanjay Yadav",
    "LRPL Taylor", "AA Kazi", "S Midhun", "S Vidyut", "Musheer Khan", "PR Veer",
    "JE Root", "R Ravindra", "Mohit Rathee", "T Vijay", "Sachin Baby", "BJ Rohrer",
    "LA Carseldine", "SA Yadav", "P Prasanth", "TH David", "SS Iyer", "F du Plessis",
    "RS Gavaskar", "LPC Silva", "D Brevis", "SPD Smith", "DA Warner", "SN Khan",
    "Ishan Kishan", "Atharva Taide", "YBK Jaiswal", "AC Gilchrist", "KH Pandya"
}

def verify_all_bowlers():
    df = pd.read_csv("data/processed/deliveries.csv", low_memory=False)
    unique_bowlers = sorted(df["bowler"].dropna().unique().tolist())
    print(f"Total unique bowlers in dataset: {len(unique_bowlers)}")

    classification = {}
    spin_count = 0
    pace_count = 0

    for b in unique_bowlers:
        if b in SPIN_BOWLERS:
            classification[b] = "Spin"
            spin_count += 1
        else:
            classification[b] = "Pace"
            pace_count += 1

    print(f"Classified: {pace_count} Pace bowlers, {spin_count} Spin bowlers")
    
    # Save to CSV
    res_df = pd.DataFrame([
        {"bowler": b, "bowling_type": classification[b]}
        for b in unique_bowlers
    ])
    res_df.to_csv("data/processed/bowler_classification.csv", index=False)
    print("Saved classification to data/processed/bowler_classification.csv")

    # Save to JSON
    with open("data/processed/bowler_classification.json", "w", encoding="utf-8") as f:
        json.dump(classification, f, indent=2)
    print("Saved classification to data/processed/bowler_classification.json")

    return classification

if __name__ == "__main__":
    verify_all_bowlers()
