#!/usr/bin/env python3
"""
CricImpact: Automated Player Portrait Collection and Integration Pipeline
-------------------------------------------------------------------------
Discovers, verifies, downloads, optimizes, and maps open-access player portraits
for the CricImpact canonical cricket database.

Strictly enforces:
- Open-access reuse verification (CC0, CC BY, CC BY-SA, GODL-India, Public Domain)
- Rejection of unverified/copyrighted/fair-use images with audit reasons
- MediaWiki / Wikimedia Commons API compliance
- High-efficiency WebP conversion and consistent headshot cropping
- Idempotent execution (preserves manually curated portraits and existing attributions)
- Multi-competition canonical player identity and alias resolution
"""

import os
import sys
import re
import io
import json
import time
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import pandas as pd
from PIL import Image

# Workspace Paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
ASSETS_DIR = FRONTEND_DIR / "public" / "assets" / "players"
ATTRIBUTION_PATH = ASSETS_DIR / "ATTRIBUTION.md"
IMAGES_JSON_PATH = FRONTEND_DIR / "src" / "constants" / "playerImages.json"
IMAGES_JS_PATH = FRONTEND_DIR / "src" / "constants" / "playerImages.js"
DATA_DIR = ROOT_DIR / "data"
SCRATCH_DIR = ROOT_DIR / "scratch"
CACHE_PATH = DATA_DIR / "portrait_discovery_cache.json"

USER_AGENT = "CricImpactPortraitBot/1.0 (https://cricimpact.onrender.com; contact@cricimpact.org)"

# Approved Open-Access Licenses
APPROVED_LICENSES = {
    "cc0",
    "public domain",
    "pd",
    "cc by",
    "cc by 2.0",
    "cc by 2.5",
    "cc by 3.0",
    "cc by 4.0",
    "cc by-sa",
    "cc by-sa 2.0",
    "cc by-sa 2.5",
    "cc by-sa 3.0",
    "cc by-sa 4.0",
    "godl-india",
    "cc-by-sa-4.0",
    "cc-by-sa-3.0",
    "cc-by-3.0",
    "cc-by-2.0",
    "cc by 3.0 nz",
    "open government licence",
    "custom (godl-india)",
}

DISALLOWED_LICENSE_TERMS = [
    "noncommercial",
    "-nc",
    "noderivatives",
    "-nd",
    "fair use",
    "all rights reserved",
    "copyrighted free use",
]

INANIMATE_OBJECT_PATTERNS = [
    r"logo",
    r"flag",
    r"map",
    r"scorecard",
    r"bat\b",
    r"ball\b",
    r"jersey",
    r"emblem",
    r"signature",
    r"autograph",
    r"icon",
    r"diagram",
    r"chart",
    r"graph",
    r"medal",
    r"poster",
    r"banner",
    r"drawing",
    r"illustration",
    r"silhouette",
    r"collage",
]


def slugify_name(name: str) -> str:
    """Produces clean kebab-case slug for filenames and URL keys."""
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def is_license_approved(license_name: str) -> Tuple[bool, str]:
    """Validates license string against strict open-access criteria."""
    if not license_name:
        return False, "LICENSE_UNVERIFIED"
    l_lower = license_name.strip().lower()

    for disallowed in DISALLOWED_LICENSE_TERMS:
        if disallowed in l_lower:
            return False, f"DISALLOWED_LICENSE_{disallowed.upper().replace(' ', '_')}"

    for approved in APPROVED_LICENSES:
        if approved in l_lower:
            return True, "APPROVED"

    return False, "LICENSE_UNVERIFIED"


# Comprehensive canonical full names and aliases dictionary for cricket stars
CRICKET_CANONICAL_FULL_NAMES: Dict[str, str] = {
    "sa yadav": "Suryakumar Yadav",
    "ka pollard": "Kieron Pollard",
    "mr marsh": "Mitchell Marsh",
    "jj bumrah": "Jasprit Bumrah",
    "ch gayle": "Chris Gayle",
    "dj bravo": "Dwayne Bravo",
    "spd smith": "Steve Smith",
    "ks williamson": "Kane Williamson",
    "ta boult": "Trent Boult",
    "pj cummins": "Pat Cummins",
    "ma starc": "Mitchell Starc",
    "babar azam": "Babar Azam",
    "rashid khan": "Rashid Khan",
    "so hetmyer": "Shimron Hetmyer",
    "n pooran": "Nicholas Pooran",
    "q de kock": "Quinton de Kock",
    "h klaasen": "Heinrich Klaasen",
    "th david": "Tim David",
    "r tewatia": "Rahul Tewatia",
    "rk singh": "Rinku Singh",
    "mm ali": "Moeen Ali",
    "ba stokes": "Ben Stokes",
    "sm curran": "Sam Curran",
    "jc archer": "Jofra Archer",
    "cj jordan": "Chris Jordan",
    "cr woakes": "Chris Woakes",
    "ma wood": "Mark Wood",
    "aj finch": "Aaron Finch",
    "mp stoinis": "Marcus Stoinis",
    "ms wade": "Matthew Wade",
    "a zampa": "Adam Zampa",
    "jr hazlewood": "Josh Hazlewood",
    "kw richardson": "Kane Richardson",
    "ja richardson": "Jhye Richardson",
    "dr sams": "Daniel Sams",
    "nt ellis": "Nathan Ellis",
    "nathan ellis": "Nathan Ellis",
    "sn thakur": "Shardul Thakur",
    "dl chahar": "Deepak Chahar",
    "rd chahar": "Rahul Chahar",
    "cv varun": "Varun Chakravarthy",
    "t natarajan": "T Natarajan",
    "washington sundar": "Washington Sundar",
    "kh pandya": "Krunal Pandya",
    "mk pandey": "Manish Pandey",
    "kd karthik": "Dinesh Karthik",
    "wp saha": "Wriddhiman Saha",
    "at rayudu": "Ambati Rayudu",
    "yk pathan": "Yusuf Pathan",
    "ik pathan": "Irfan Pathan",
    "harbhajan singh": "Harbhajan Singh",
    "z khan": "Zaheer Khan",
    "a nehra": "Ashish Nehra",
    "rp singh": "RP Singh",
    "p kumar": "Praveen Kumar",
    "v sehwag": "Virender Sehwag",
    "g gambhir": "Gautam Gambhir",
    "sr tendulkar": "Sachin Tendulkar",
    "sc ganguly": "Sourav Ganguly",
    "r dravid": "Rahul Dravid",
    "vvs laxman": "VVS Laxman",
    "a kumble": "Anil Kumble",
    "m muralitharan": "Muttiah Muralitharan",
    "sl malinga": "Lasith Malinga",
    "kc sangakkara": "Kumar Sangakkara",
    "dpmd jayawardene": "Mahela Jayawardene",
    "tm dilshan": "Tillakaratne Dilshan",
    "nltc perera": "Thisara Perera",
    "b lee": "Brett Lee",
    "sr watson": "Shane Watson",
    "mek hussey": "Michael Hussey",
    "dj hussey": "David Hussey",
    "ac gilchrist": "Adam Gilchrist",
    "ml hayden": "Matthew Hayden",
    "a symonds": "Andrew Symonds",
    "sk warne": "Shane Warne",
    "jh kallis": "Jacques Kallis",
    "gc smith": "Graeme Smith",
    "dw steyn": "Dale Steyn",
    "m ntini": "Makhaya Ntini",
    "ja morkel": "Albie Morkel",
    "m morkel": "Morne Morkel",
    "shubman gill": "Shubman Gill",
    "ishan kishan": "Ishan Kishan",
    "ybk jaiswal": "Yashasvi Jaiswal",
    "tilak varma": "Tilak Varma",
    "nt tilak varma": "Tilak Varma",
    "r parag": "Riyan Parag",
    "abhishek sharma": "Abhishek Sharma",
    "arshdeep singh": "Arshdeep Singh",
    "mukesh kumar": "Mukesh Kumar",
    "avesh khan": "Avesh Khan",
    "harshit rana": "Harshit Rana",
    "mayank yadav": "Mayank Yadav",
    "dhruv jurel": "Dhruv Jurel",
    "jitesh sharma": "Jitesh Sharma",
    "shivam dube": "Shivam Dube",
    "s dube": "Shivam Dube",
    "vr iyer": "Venkatesh Iyer",
    "ss iyer": "Shreyas Iyer",
    "pp chawla": "Piyush Chawla",
    "a mishra": "Amit Mishra",
    "mm sharma": "Mohit Sharma",
    "sandeep sharma": "Sandeep Sharma",
    "ra tripathi": "Rahul Tripathi",
    "n rana": "Nitish Rana",
    "kk nair": "Karun Nair",
    "ma agarwal": "Mayank Agarwal",
    "d padikkal": "Devdutt Padikkal",
    "ad russell": "Andre Russell",
    "sp narine": "Sunil Narine",
    "f du plessis": "Faf du Plessis",
    "rg sharma": "Rohit Sharma",
    "v kohli": "Virat Kohli",
    "ms dhoni": "MS Dhoni",
    "ra jadeja": "Ravindra Jadeja",
    "hh pandya": "Hardik Pandya",
    "s dhawan": "Shikhar Dhawan",
    "sv samson": "Sanju Samson",
    "rr pant": "Rishabh Pant",
    "kl rahul": "KL Rahul",
    "da warner": "David Warner",
    "ab de villiers": "AB de Villiers",
    "sk raina": "Suresh Raina",
    "ys chahal": "Yuzvendra Chahal",
    "ar patel": "Axar Patel",
    "b kumar": "Bhuvneshwar Kumar",
    "am rahane": "Ajinkya Rahane",
    "rv uthappa": "Robin Uthappa",
    "hc brook": "Harry Brook",
    "rd gaikwad": "Ruturaj Gaikwad",
    "pp shaw": "Prithvi Shaw",
    "ut yadav": "Umesh Yadav",
}


class PlayerPortraitManager:
    def __init__(self):
        self.cache: Dict[str, Any] = self._load_cache()
        self.people_df: Optional[pd.DataFrame] = None
        self.names_df: Optional[pd.DataFrame] = None
        self._load_cricsheet_registers()

    def _load_cache(self) -> Dict[str, Any]:
        if CACHE_PATH.exists():
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_cache(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def _load_cricsheet_registers(self):
        """Loads or downloads official Cricsheet people and names registers."""
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        people_p = SCRATCH_DIR / "people.csv"
        names_p = SCRATCH_DIR / "names.csv"

        if not people_p.exists():
            print("Downloading Cricsheet people.csv...")
            urllib.request.urlretrieve("https://cricsheet.org/register/people.csv", people_p)
        if not names_p.exists():
            print("Downloading Cricsheet names.csv...")
            urllib.request.urlretrieve("https://cricsheet.org/register/names.csv", names_p)

        self.people_df = pd.read_csv(people_p, low_memory=False)
        self.names_df = pd.read_csv(names_p, low_memory=False)

    def get_canonical_players(self) -> Dict[str, Dict[str, Any]]:
        """
        Gathers all unique canonical players from active datasets (IPL and T20I),
        enriched with Cricsheet identifier, full name, and known aliases.
        """
        players: Dict[str, Dict[str, Any]] = {}

        # 1. IPL metrics
        ipl_metrics = ROOT_DIR / "models" / "contribution" / "phase6" / "phase6_season_metrics.csv"
        if ipl_metrics.exists():
            df = pd.read_csv(ipl_metrics, usecols=["player", "matches_played", "actual_runs"])
            agg = df.groupby("player").agg({"matches_played": "sum", "actual_runs": "sum"}).reset_index()
            for _, r in agg.iterrows():
                p = str(r["player"]).strip()
                players[p] = {
                    "canonical_name": p,
                    "in_ipl": True,
                    "in_t20i": False,
                    "matches": int(r["matches_played"]),
                    "runs": int(r["actual_runs"]),
                }

        # 2. T20I metrics
        t20i_metrics = ROOT_DIR / "data" / "processed" / "t20i" / "phase6_season_metrics.csv"
        if t20i_metrics.exists():
            df = pd.read_csv(t20i_metrics, usecols=["player", "matches_played", "actual_runs"])
            agg = df.groupby("player").agg({"matches_played": "sum", "actual_runs": "sum"}).reset_index()
            for _, r in agg.iterrows():
                p = str(r["player"]).strip()
                if p in players:
                    players[p]["in_t20i"] = True
                    players[p]["matches"] += int(r["matches_played"])
                    players[p]["runs"] += int(r["actual_runs"])
                else:
                    players[p] = {
                        "canonical_name": p,
                        "in_ipl": False,
                        "in_t20i": True,
                        "matches": int(r["matches_played"]),
                        "runs": int(r["actual_runs"]),
                    }

        # Enrich with aliases from Cricsheet & canonical full names
        people = self.people_df
        names = self.names_df

        name_to_ids: Dict[str, Set[str]] = {}
        for _, r in names.iterrows():
            n = str(r["name"]).strip()
            i = str(r["identifier"]).strip()
            name_to_ids.setdefault(n.lower(), set()).add(i)

        unique_to_id: Dict[str, str] = {}
        for _, r in people.iterrows():
            u = str(r["unique_name"]).strip()
            i = str(r["identifier"]).strip()
            unique_to_id[u.lower()] = i

        for p_name, meta in players.items():
            p_lower = p_name.lower()
            pid = unique_to_id.get(p_lower)
            if not pid and p_lower in name_to_ids:
                cands = list(name_to_ids[p_lower])
                if len(cands) == 1:
                    pid = cands[0]

            meta["cricsheet_id"] = pid
            aliases = set()
            full_name = CRICKET_CANONICAL_FULL_NAMES.get(p_lower)

            if pid:
                p_names = names[names["identifier"] == pid]["name"].tolist()
                for n in p_names:
                    aliases.add(str(n).strip())
                if not full_name:
                    multi_words = [n for n in p_names if " " in str(n).strip()]
                    if multi_words:
                        full_name = max(multi_words, key=lambda x: len(str(x)))

            if not full_name:
                full_name = p_name

            if full_name and full_name != p_name:
                aliases.add(full_name)

            meta["full_name"] = full_name
            meta["aliases"] = sorted(aliases)

        return players

    def query_wikimedia_api(self, url: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    def search_wikipedia_cricketer(self, full_name: str, canonical_name: str) -> List[str]:
        """Discovers relevant Wikipedia article titles for a cricketer."""
        candidates = []

        # 1. Direct title checks
        candidates.append(full_name)
        if f"{full_name} (cricketer)" != full_name:
            candidates.append(f"{full_name} (cricketer)")
        if canonical_name != full_name:
            candidates.append(canonical_name)
            candidates.append(f"{canonical_name} (cricketer)")

        # 2. Search API query
        params = {
            "action": "query",
            "list": "search",
            "srsearch": f'"{full_name}" cricketer',
            "format": "json",
            "srlimit": "4",
        }
        res = self.query_wikimedia_api("https://en.wikipedia.org/w/api.php", params)
        if res:
            search_items = res.get("query", {}).get("search", [])
            for item in search_items:
                title = item.get("title")
                snippet = item.get("snippet", "").lower()
                # Verify cricket relevance and skip lists / discographies / movie pages
                if any(k in snippet for k in ["cricket", "batsman", "bowler", "ipl", "t20", "wicket"]):
                    if not any(k in title.lower() for k in ["list of", "season", "film", "movie", "song", "album"]):
                        if title not in candidates:
                            candidates.append(title)

        return candidates

    def get_article_lead_image(self, title: str) -> Optional[str]:
        """Retrieves pageimage filename for a Wikipedia article."""
        params = {
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "format": "json",
            "pithumbsize": "600",
        }
        res = self.query_wikimedia_api("https://en.wikipedia.org/w/api.php", params)
        if not res:
            return None
        pages = res.get("query", {}).get("pages", {})
        for pid, p in pages.items():
            if pid != "-1" and "pageimage" in p:
                return p["pageimage"]
        return None

    def search_commons_candidates(self, full_name: str) -> List[str]:
        """Searches Wikimedia Commons directly for candidate image files."""
        candidates = []
        # Query category files if Category exists
        cat_params = {
            "action": "query",
            "generator": "categorymembers",
            "gcmtitle": f"Category:{full_name}",
            "gcmtype": "file",
            "gcmlimit": "8",
            "format": "json",
        }
        res = self.query_wikimedia_api("https://commons.wikimedia.org/w/api.php", cat_params)
        if res:
            pages = res.get("query", {}).get("pages", {})
            for p in pages.values():
                title = p.get("title", "").replace("File:", "")
                if title and title not in candidates:
                    candidates.append(title)

        # Also search files matching player name
        if not candidates:
            search_params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": f'"{full_name}"',
                "gsrnamespace": "6",
                "gsrlimit": "5",
                "format": "json",
            }
            s_res = self.query_wikimedia_api("https://commons.wikimedia.org/w/api.php", search_params)
            if s_res:
                s_pages = s_res.get("query", {}).get("pages", {})
                for p in s_pages.values():
                    title = p.get("title", "").replace("File:", "")
                    if title and title not in candidates:
                        candidates.append(title)

        return candidates

    def get_commons_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Queries Wikimedia Commons for file metadata, URL, and license terms."""
        if not filename.startswith("File:"):
            filename = "File:" + filename

        params = {
            "action": "query",
            "titles": filename,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime",
            "format": "json",
        }
        res = self.query_wikimedia_api("https://commons.wikimedia.org/w/api.php", params)
        if not res:
            return None

        pages = res.get("query", {}).get("pages", {})
        for pid, p in pages.items():
            if pid != "-1" and "imageinfo" in p:
                ii = p["imageinfo"][0]
                meta = ii.get("extmetadata", {})
                artist_raw = meta.get("Artist", {}).get("value", "")
                artist_clean = re.sub(r"<[^>]+>", "", artist_raw).strip()
                if not artist_clean or len(artist_clean) > 80:
                    artist_clean = re.sub(r"\s+", " ", artist_clean)[:60]
                if not artist_clean:
                    credit_raw = meta.get("Credit", {}).get("value", "")
                    artist_clean = re.sub(r"<[^>]+>", "", credit_raw).strip()[:60]
                if not artist_clean:
                    artist_clean = "Wikimedia Commons Contributor"

                lic = meta.get("LicenseShortName", {}).get("value", "")
                lic_url = meta.get("LicenseUrl", {}).get("value", "")
                if not lic_url and "godl" in lic.lower():
                    lic_url = "https://data.gov.in/sites/default/files/Gazette_Notification_OGDL.pdf"
                elif not lic_url and "cc0" in lic.lower():
                    lic_url = "https://creativecommons.org/publicdomain/zero/1.0/"

                desc = meta.get("ObjectName", {}).get("value") or meta.get("ImageDescription", {}).get("value") or ""
                desc_clean = re.sub(r"<[^>]+>", "", desc).strip()

                return {
                    "filename": filename.replace("File:", ""),
                    "url": ii.get("url"),
                    "mime": ii.get("mime", ""),
                    "width": ii.get("width", 0),
                    "height": ii.get("height", 0),
                    "license": lic,
                    "license_url": lic_url,
                    "artist": artist_clean,
                    "description": desc_clean,
                }
        return None

    def evaluate_candidate_image(
        self, canonical_name: str, full_name: str, aliases: List[str]
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Discovers candidate images for a player and evaluates their reuse suitability.
        Returns (approved_metadata_or_none, decision_reason).
        """
        cache_key = f"{canonical_name}::{full_name}"
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if entry.get("status") == "APPROVED":
                return entry.get("metadata"), "APPROVED"
            elif entry.get("status") == "REJECTED":
                return None, entry.get("reason", "PREVIOUSLY_REJECTED")

        # Discover candidate files in priority order:
        # Priority 1: Wikimedia Commons category / search
        # Priority 2: Wikipedia article lead image
        candidate_files: List[Tuple[str, str, int]] = []  # (source_context, filename, priority_score)

        # 1. Commons candidates
        commons_files = self.search_commons_candidates(full_name)
        for cf in commons_files:
            score = 10
            cf_lower = cf.lower()
            if "cropped" in cf_lower or "portrait" in cf_lower or "headshot" in cf_lower:
                score += 20
            candidate_files.append(("Wikimedia Commons", cf, score))

        # 2. Wikipedia article lead images
        titles = self.search_wikipedia_cricketer(full_name, canonical_name)
        for title in titles:
            lead_img = self.get_article_lead_image(title)
            if lead_img and not any(cf == lead_img for _, cf, _ in candidate_files):
                score = 15
                if "cropped" in lead_img.lower() or "portrait" in lead_img.lower():
                    score += 20
                candidate_files.append((title, lead_img, score))

        if not candidate_files:
            self.cache[cache_key] = {"status": "REJECTED", "reason": "IMAGE_UNAVAILABLE"}
            return None, "IMAGE_UNAVAILABLE"

        # Sort candidate files by priority score descending
        candidate_files.sort(key=lambda x: x[2], reverse=True)

        name_parts = set(full_name.lower().split() + canonical_name.lower().split())
        name_parts.discard("")

        last_rejection_reason = "IMAGE_UNAVAILABLE"

        for context, filename, _ in candidate_files:
            fn_lower = filename.lower()

            # Reject inanimate objects unconditionally
            if any(re.search(pat, fn_lower) for pat in INANIMATE_OBJECT_PATTERNS):
                last_rejection_reason = "NON_PERSON_IMAGE"
                continue

            # Reject standalone stadium/ground photos unless the player's name is in the filename
            has_player_in_fn = any(p in fn_lower for p in name_parts if len(p) > 2)
            if ("stadium" in fn_lower or "ground" in fn_lower) and not has_player_in_fn:
                last_rejection_reason = "NON_PERSON_IMAGE"
                continue

            # Fetch file metadata from Commons
            info = self.get_commons_file_info(filename)
            if not info:
                last_rejection_reason = "METADATA_UNAVAILABLE"
                continue

            # Verify image format and dimensions
            mime = info.get("mime", "")
            if mime not in ("image/jpeg", "image/png", "image/webp"):
                last_rejection_reason = "UNSUPPORTED_FORMAT"
                continue

            w = info.get("width", 0)
            h = info.get("height", 0)
            if w < 160 or h < 160:
                last_rejection_reason = "IMAGE_TOO_SMALL"
                continue

            # Aspect ratio check
            if w > 2.5 * h or h > 3.2 * w:
                last_rejection_reason = "EXTREME_ASPECT_RATIO"
                continue

            # Check license approval
            lic = info.get("license", "")
            approved, lic_reason = is_license_approved(lic)
            if not approved:
                last_rejection_reason = lic_reason
                continue

            # Identity verification: verify relevance to player
            combined_text = (filename + " " + info.get("description", "") + " " + context).lower()
            matches_identity = any(p in combined_text for p in name_parts if len(p) > 2)
            if not matches_identity and canonical_name.lower() not in combined_text:
                last_rejection_reason = "IDENTITY_UNCERTAIN"
                continue

            # Candidate passed all checks!
            meta = {
                "canonical_name": canonical_name,
                "full_name": full_name,
                "source_file": filename,
                "commons_url": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(filename)}",
                "download_url": info["url"],
                "author": info["artist"],
                "license": info["license"],
                "license_url": info["license_url"],
            }
            self.cache[cache_key] = {"status": "APPROVED", "metadata": meta}
            return meta, "APPROVED"

        self.cache[cache_key] = {"status": "REJECTED", "reason": last_rejection_reason}
        return None, last_rejection_reason

    def process_and_optimize_image(self, meta: Dict[str, Any], dest_path: Path) -> bool:
        """Downloads, validates, crops headshot, and converts to optimized WebP."""
        download_url = meta.get("download_url")
        if not download_url:
            return False

        req = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "image" not in content_type:
                    return False
                raw_bytes = resp.read()

            if len(raw_bytes) > 25 * 1024 * 1024 or len(raw_bytes) < 1000:
                return False

            img = Image.open(io.BytesIO(raw_bytes))
            # Convert to RGB if needed (handling RGBA / P modes)
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (18, 18, 18))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

            w, h = img.size
            if h > w:
                # Portrait orientation: crop upper face/headshot region (shifted slightly down from top)
                top = int(h * 0.03)
                bottom = top + w
                if bottom > h:
                    bottom = h
                    top = max(0, bottom - w)
                img_cropped = img.crop((0, top, w, bottom))
            elif w > h:
                # Landscape orientation: center square crop
                diff = w - h
                left = diff // 2
                right = left + h
                img_cropped = img.crop((left, 0, right, h))
            else:
                img_cropped = img

            # Resize to standard 320x320
            final_img = img_cropped.resize((320, 320), Image.Resampling.LANCZOS)

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            final_img.save(dest_path, format="WEBP", quality=82, method=6)
            return True
        except Exception as e:
            print(f"Error processing image for {meta.get('canonical_name')}: {e}")
            return False


def load_existing_attributions() -> Dict[str, Dict[str, str]]:
    """Parses existing ATTRIBUTION.md into structured records keyed by canonical ID."""
    records = {}
    if not ATTRIBUTION_PATH.exists():
        return records

    content = ATTRIBUTION_PATH.read_text(encoding="utf-8")
    table_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("|")]

    for line in table_lines:
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) >= 5 and parts[0] != "Player" and not parts[0].startswith(":"):
            player_name = parts[0]
            canonical_id = parts[1].replace("`", "").strip()
            author = parts[2]
            license_md = parts[3]
            source_md = parts[4]
            records[canonical_id] = {
                "player": player_name,
                "canonical_id": canonical_id,
                "author": author,
                "license": license_md,
                "source": source_md,
            }
    return records


def update_attribution_file(records: Dict[str, Dict[str, str]]):
    """Generates formatted ATTRIBUTION.md retaining policies and complete tables."""
    lines = [
        "# Verified Player Image Assets & Licensing",
        "",
        "## 1. Compliance & Redistribution Policy",
        "To ensure strict copyright compliance, CricImpact bundles **only player portraits whose individual open-access licenses and redistribution permissions have been verified**.",
        "",
        "All proprietary photographs from commercial media (ESPNcricinfo, Getty Images, IPL/BCCI, and franchise sites) have been completely removed from this repository. For players without a verified open-access portrait, CricImpact uses its native **Gold & Onyx monogram fallback avatar**.",
        "",
        "Initial player catalog metadata and name mappings were adapted from the Apache-2.0 licensed [Shaurya01836/ipl-auction](https://github.com/Shaurya01836/ipl-auction) repository (Copyright (c) 2026 Shaurya Upadhyay).",
        "",
        "## 2. Retained Portraits (Wikimedia Commons & Open-Access Sources)",
        "",
        "| Player | Canonical ID | Author / Creator | License | Original Source |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    # Sort records alphabetically by player name
    sorted_records = sorted(records.values(), key=lambda r: r["player"].lower())
    for r in sorted_records:
        lines.append(
            f"| {r['player']} | `{r['canonical_id']}` | {r['author']} | {r['license']} | {r['source']} |"
        )

    lines.extend([
        "",
        "## 3. License Terms",
        "- **Creative Commons (CC BY-SA 4.0, 3.0, 2.0; CC BY 4.0, 3.0, 2.0; CC BY 3.0 NZ):** Permitted for distribution and modification with author attribution and identical license sharing where applicable.",
        "- **Government Open Data License - India (GODL-India):** Public domain / open government data license permitting worldwide, royalty-free reuse and redistribution.",
        "- **CC0 / Public Domain:** Dedicated to the public domain without copyright restrictions.",
        "",
    ])

    ATTRIBUTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    ATTRIBUTION_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_mapping_files(canonical_players: Dict[str, Dict[str, Any]], working_assets: Dict[str, str]):
    """
    Writes updated playerImages.json and playerImages.js.
    Maps canonical names, full names, and clean aliases to approved assets.
    Excludes ambiguous aliases that match multiple players.
    """
    mapping: Dict[str, str] = {}

    alias_to_players: Dict[str, Set[str]] = {}
    for p_name, meta in canonical_players.items():
        candidates = [p_name]
        if meta.get("full_name"):
            candidates.append(meta["full_name"])
        candidates.extend(meta.get("aliases", []))
        for cand in candidates:
            alias_to_players.setdefault(cand.strip().lower(), set()).add(p_name)

    # Special handling for known canonical pairings like Rasikh Salam <-> Rasikh Dar
    alias_to_players["rasikh dar"] = {"Rasikh Salam"}
    alias_to_players["rasikh-dar"] = {"Rasikh Salam"}

    for p_name, meta in canonical_players.items():
        asset_url = working_assets.get(p_name)
        if not asset_url:
            continue

        keys_to_map = [p_name]
        if meta.get("full_name") and meta["full_name"] != p_name:
            keys_to_map.append(meta["full_name"])
        for a in meta.get("aliases", []):
            if a != p_name:
                keys_to_map.append(a)

        # Support Rasikh Salam / Rasikh Dar alias explicitly
        if p_name == "Rasikh Salam":
            keys_to_map.extend(["Rasikh Dar", "rasikh dar", "rasikh-dar", "rasikhdar"])

        for k in keys_to_map:
            k_clean = k.strip()
            if not k_clean:
                continue
            k_lower = k_clean.lower()
            # Guard against ambiguous alias mapping
            matched_players = alias_to_players.get(k_lower, set())
            if len(matched_players) > 1 and p_name not in ("Rasikh Salam", "Rasikh Dar"):
                continue

            slug = slugify_name(k_clean)
            compact = slug.replace("-", "")

            mapping[k_clean] = asset_url
            mapping[k_lower] = asset_url
            if slug:
                mapping[slug] = asset_url
            if compact:
                mapping[compact] = asset_url

    # Write playerImages.json
    with open(IMAGES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    # Write playerImages.js
    js_content = [
        "// Verified open-source player image mapping manifest",
        "// Auto-generated by scripts/acquire_player_portraits.py",
        f"export const PLAYER_IMAGES = {json.dumps(mapping, indent=2, ensure_ascii=False)};",
        "",
        "export default PLAYER_IMAGES;",
        "",
    ]
    with open(IMAGES_JS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(js_content))


def run_pipeline(target_cohort: str = "ipl", limit: Optional[int] = None, dry_run: bool = False):
    print("=" * 70)
    print("CricImpact Player Portrait Acquisition & Mapping Pipeline")
    print("=" * 70)

    manager = PlayerPortraitManager()
    canonical_players = manager.get_canonical_players()
    attributions = load_existing_attributions()

    working_assets: Dict[str, str] = {}

    existing_file_map = {
        "JC Buttler": "jc-buttler.webp",
        "Mohammed Shami": "mohammed-shami.webp",
        "RD Gaikwad": "rd-gaikwad.webp",
        "LH Ferguson": "lh-ferguson.webp",
        "PP Shaw": "pp-shaw.webp",
        "Arjun Tendulkar": "arjun-tendulkar.webp",
        "Rasikh Salam": "rasikh-dar.webp",
        "Rasikh Dar": "rasikh-dar.webp",
        "BM Duckett": "bm-duckett.webp",
        "Anmolpreet Singh": "anmolpreet-singh.webp",
        "Sanvir Singh": "sanvir-singh.webp",
        "KV Sharma": "kv-sharma.webp",
        "JO Holder": "jo-holder.webp",
        "JP Inglis": "jp-inglis.webp",
        "KA Jamieson": "ka-jamieson.webp",
        "L Ngidi": "l-ngidi.webp",
        "UT Yadav": "ut-yadav.webp",
    }

    for p_name, fname in existing_file_map.items():
        if (ASSETS_DIR / fname).exists():
            working_assets[p_name] = f"/assets/players/{fname}"
            if p_name == "Rasikh Dar":
                working_assets["Rasikh Salam"] = f"/assets/players/{fname}"

    # Also detect all approved webp files present on disk
    for p_name in canonical_players:
        if p_name not in working_assets:
            slug = slugify_name(p_name)
            if (ASSETS_DIR / f"{slug}.webp").exists():
                working_assets[p_name] = f"/assets/players/{slug}.webp"

    # Filter target players according to cohort
    if target_cohort == "ipl":
        target_players = {p: meta for p, meta in canonical_players.items() if meta["in_ipl"]}
    elif target_cohort == "t20i":
        target_players = {p: meta for p, meta in canonical_players.items() if meta["in_t20i"]}
    else:
        target_players = canonical_players

    # Sort target players by match count (prioritizing high-profile players)
    sorted_players = sorted(target_players.items(), key=lambda kv: kv[1]["matches"], reverse=True)

    missing_players = [(p, meta) for p, meta in sorted_players if p not in working_assets]

    print(f"Total Canonical Players in Active Database: {len(canonical_players)}")
    print(f"Total Players in Target Cohort ({target_cohort}): {len(target_players)}")
    print(f"Players with Working Portraits Currently: {len([p for p in target_players if p in working_assets])}")
    print(f"Players Missing Portraits in Target Cohort: {len(missing_players)}")
    initial_cov = (len([p for p in target_players if p in working_assets]) / len(target_players)) * 100
    print(f"Initial Portrait Coverage: {initial_cov:.2f}%\n")

    if limit is not None:
        print(f"Applying execution limit: processing first {limit} missing players.")
        missing_players = missing_players[:limit]

    new_portraits_added = 0
    rejections: Dict[str, List[str]] = {}

    for idx, (p_name, meta) in enumerate(missing_players, 1):
        full_name = meta.get("full_name", p_name)
        slug = slugify_name(p_name)
        dest_file = ASSETS_DIR / f"{slug}.webp"

        print(f"[{idx}/{len(missing_players)}] Searching: {p_name} ({full_name}) ...", end=" ", flush=True)

        approved_meta, reason = manager.evaluate_candidate_image(p_name, full_name, meta.get("aliases", []))

        if approved_meta and not dry_run:
            success = manager.process_and_optimize_image(approved_meta, dest_file)
            if success:
                new_portraits_added += 1
                working_assets[p_name] = f"/assets/players/{slug}.webp"

                lic_str = approved_meta["license"]
                lic_url = approved_meta.get("license_url", "")
                if lic_url:
                    lic_md = f"[{lic_str}]({lic_url})"
                else:
                    lic_md = lic_str

                src_url = approved_meta.get("commons_url", approved_meta.get("download_url"))
                src_md = f"[Wikimedia Commons File]({src_url})"

                attributions[p_name] = {
                    "player": full_name,
                    "canonical_id": p_name,
                    "author": approved_meta.get("author", "Unknown"),
                    "license": lic_md,
                    "source": src_md,
                }
                print(f"APPROVED & SAVED ({approved_meta['license']})")
            else:
                rejections.setdefault("DOWNLOAD_FAILED", []).append(p_name)
                print("FAILED TO DOWNLOAD/PROCESS")
        elif approved_meta and dry_run:
            print(f"[DRY-RUN] APPROVED: {approved_meta['license']}")
        else:
            rejections.setdefault(reason, []).append(p_name)
            print(f"REJECTED ({reason})")

        time.sleep(0.08)

    manager.save_cache()

    if not dry_run:
        update_attribution_file(attributions)
        update_mapping_files(canonical_players, working_assets)

    final_cov_target = (len([p for p in target_players if p in working_assets]) / len(target_players)) * 100
    final_cov_all = (len([p for p in canonical_players if p in working_assets]) / len(canonical_players)) * 100

    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Target Cohort: {target_cohort}")
    print(f"Total Unique Canonical Players: {len(canonical_players)}")
    print(f"Initial Approved Portraits: {len(existing_file_map)}")
    print(f"New Portraits Added: {new_portraits_added}")
    print(f"Total Working Portraits Now: {len(working_assets)}")
    print(f"Portrait Coverage ({target_cohort}): {final_cov_target:.2f}%")
    print(f"Overall Canonical Portrait Coverage: {final_cov_all:.2f}%")
    print("\nRejection Breakdown:")
    for reason, plist in rejections.items():
        print(f"  - {reason}: {len(plist)} players (e.g. {', '.join(plist[:3])})")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Automated Player Portrait Acquisition & Integration")
    parser.add_argument("--cohort", choices=["ipl", "t20i", "all"], default="ipl", help="Target competition cohort")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of missing players to evaluate")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate candidates without downloading")
    args = parser.parse_args()

    run_pipeline(target_cohort=args.cohort, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
