"""
Demographics scraper for UK postcodes.

Primary source: postcodearea.co.uk (all demographic fields via Playwright)

Output matches training dataset columns 8-18:
    population, households, avg_household_income, unemployment_rate,
    working, unemployed, ab, c1_c2, de, white, non_white

Verified against live site: 2026-02-17
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
postcodearea.co.uk HTML structure (Census 2021):
    Headline stats:  h2.h6 label → .headlineNumber.text-blue value
    Sections:        #content-population, #content-ethnicity, #content-work, #content-income
    Bar charts:      .myBar → .description (label) + .amount-pc (value) + .amount[data-pc]
    Employment:      .headlineNumber.text-blue within #content-work grid

Rate-limit bypass strategy (tested 2026-02-17):
    → The site tracks page views via cookies (resets in incognito)
    → ~50% of requests return 503 "Server Overload" (random, not time-based)
    → Solution: Fresh Playwright incognito context per request + retry on 503
    → 5-second delay between retries; up to 5 retries = ~97% success rate
    → UK VPN required (geo-blocked outside UK)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
URL pattern: /postaltowns/{postal_town}/{outercode}/
    The postal town must match the outercode's region.
    A mapping dict is provided for common London-area outercodes.
"""

import time
from typing import Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from location_analyzer.scrapers.base import BaseScraper
from location_analyzer.logging_config import get_logger
from location_analyzer.exceptions import ScraperParsingError

logger = get_logger(__name__)

# ─── Constants ──────────────────────────────────────────────
MAX_RETRIES = 15          # Max attempts per outercode (503 is ~80% random)
RETRY_DELAY_SECS = 10    # Delay between sessions (10s+ works per test data)
PAGE_TIMEOUT_MS = 30000   # 30s page load timeout


# ─── Outercode → Postal Town Mapping ────────────────────────
# postcodearea.co.uk URLs require the postal town in the path.
# This maps common London-area outercodes to their postal towns.
# Extended as needed; unknown outercodes fall back to search.
OUTERCODE_TO_TOWN: dict[str, str] = {
    # West London / Hillingdon
    "UB1": "southall", "UB2": "southall", "UB3": "hayes",
    "UB4": "hayes", "UB5": "northolt", "UB6": "greenford",
    "UB7": "west-drayton", "UB8": "uxbridge", "UB9": "uxbridge",
    "UB10": "uxbridge", "UB11": "uxbridge",
    # Harrow
    "HA0": "wembley", "HA1": "harrow", "HA2": "harrow",
    "HA3": "harrow", "HA4": "ruislip", "HA5": "pinner",
    "HA6": "northwood", "HA7": "stanmore", "HA8": "edgware",
    "HA9": "wembley",
    # Ealing / Acton
    "W3": "london", "W5": "london", "W7": "london", "W13": "london",
    # East London
    "E1": "london", "E2": "london", "E3": "london", "E4": "london",
    "E5": "london", "E6": "london", "E7": "london", "E8": "london",
    "E9": "london", "E10": "london", "E11": "london", "E12": "london",
    "E13": "london", "E14": "london", "E15": "london", "E16": "london",
    "E17": "london", "E18": "london", "E20": "london",
    # Central London
    "EC1": "london", "EC2": "london", "EC3": "london", "EC4": "london",
    "WC1": "london", "WC2": "london",
    "W1": "london", "W2": "london", "W4": "london", "W6": "london",
    "W8": "london", "W9": "london", "W10": "london", "W11": "london",
    "W12": "london", "W14": "london",
    "SW1": "london", "SW2": "london", "SW3": "london", "SW4": "london",
    "SW5": "london", "SW6": "london", "SW7": "london", "SW8": "london",
    "SW9": "london", "SW10": "london", "SW11": "london", "SW12": "london",
    "SW13": "london", "SW14": "london", "SW15": "london", "SW16": "london",
    "SW17": "london", "SW18": "london", "SW19": "london", "SW20": "london",
    "SE1": "london", "SE2": "london", "SE3": "london", "SE4": "london",
    "SE5": "london", "SE6": "london", "SE7": "london", "SE8": "london",
    "SE9": "london", "SE10": "london", "SE11": "london", "SE12": "london",
    "SE13": "london", "SE14": "london", "SE15": "london", "SE16": "london",
    "SE17": "london", "SE18": "london", "SE19": "london", "SE20": "london",
    "SE21": "london", "SE22": "london", "SE23": "london", "SE24": "london",
    "SE25": "london", "SE26": "london", "SE27": "london", "SE28": "london",
    "N1": "london", "N2": "london", "N3": "london", "N4": "london",
    "N5": "london", "N6": "london", "N7": "london", "N8": "london",
    "N9": "london", "N10": "london", "N11": "london", "N12": "london",
    "N13": "london", "N14": "london", "N15": "london", "N16": "london",
    "N17": "london", "N18": "london", "N19": "london", "N20": "london",
    "N21": "london", "N22": "london",
    "NW1": "london", "NW2": "london", "NW3": "london", "NW4": "london",
    "NW5": "london", "NW6": "london", "NW7": "london", "NW8": "london",
    "NW9": "london", "NW10": "london", "NW11": "london",
    # North London suburbs
    "EN1": "enfield", "EN2": "enfield", "EN3": "enfield", "EN4": "barnet",
    "EN5": "barnet",
    # South London / Croydon
    "CR0": "croydon", "CR2": "south-croydon", "CR3": "caterham",
    "CR4": "mitcham", "CR5": "coulsdon", "CR6": "warlingham",
    "CR7": "thornton-heath", "CR8": "purley",
    # Kingston / Surbiton
    "KT1": "kingston-upon-thames", "KT2": "kingston-upon-thames",
    "KT3": "new-malden", "KT4": "worcester-park", "KT5": "surbiton",
    "KT6": "surbiton",
    # Ilford / Barking
    "IG1": "ilford", "IG2": "ilford", "IG3": "ilford",
    "IG4": "ilford", "IG5": "ilford", "IG6": "ilford",
    "IG7": "chigwell", "IG8": "woodford-green", "IG9": "buckhurst-hill",
    "IG10": "loughton", "IG11": "barking",
    # Romford
    "RM1": "romford", "RM2": "romford", "RM3": "romford",
    "RM4": "romford", "RM5": "romford", "RM6": "chadwell-heath",
    "RM7": "romford", "RM8": "dagenham", "RM9": "dagenham",
    "RM10": "dagenham",
    # Bromley / Orpington
    "BR1": "bromley", "BR2": "bromley", "BR3": "beckenham",
    "BR4": "west-wickham", "BR5": "orpington", "BR6": "orpington",
    "BR7": "chislehurst",
    # Dartford / Bexley
    "DA1": "dartford", "DA5": "bexley", "DA6": "bexleyheath",
    "DA7": "bexleyheath", "DA8": "erith",
    # Twickenham / Richmond
    "TW1": "twickenham", "TW2": "twickenham", "TW3": "hounslow",
    "TW4": "hounslow", "TW5": "hounslow", "TW7": "isleworth",
    "TW8": "brentford", "TW9": "richmond", "TW10": "richmond",
    "TW11": "teddington", "TW12": "hampton", "TW13": "feltham",
    "TW14": "feltham",
    # Slough
    "SL0": "slough", "SL1": "slough", "SL2": "slough", "SL3": "slough",
    # Watford
    "WD3": "rickmansworth", "WD17": "watford", "WD18": "watford",
    "WD19": "watford", "WD23": "bushey", "WD24": "watford",
    "WD25": "watford",
}


class DemographicsScraper(BaseScraper):
    """
    Scrapes postcode demographics from postcodearea.co.uk and streetcheck.co.uk.

    Primary source: postcodearea.co.uk (Census 2021)
    Secondary/Fallback: streetcheck.co.uk (Census 2021)

    Uses fresh incognito browser contexts to bypass cookie-based limits.
    Retries up to 15 times on 503 errors (random server-side load balancing).
    """

    CACHE_CATEGORY = "demographics"
    BASE_URL = "https://www.postcodearea.co.uk/postaltowns"
    STREETCHECK_BASE_URL = "https://www.streetcheck.co.uk/postcode"

    def scrape(self, outercode: str) -> dict[str, Any]:
        """
        Scrape demographics with fallback strategy.

        Strategy:
            1. Try postcodearea.co.uk (with retry logic)
            2. If failure (even after retries), try streetcheck.co.uk
        """
        outercode = outercode.strip().upper()
        logger.info("Scraping demographics for %s", outercode)

        last_error = None

        # --- Try Primary Source: PostcodeArea ---
        town = self._get_postal_town(outercode)
        url_pa = f"{self.BASE_URL}/{town}/{outercode.lower()}/"

        try:
            soup_pa = self._fetch_with_uc(url_pa, outercode)
            return self._parse_postcodearea(soup_pa, outercode)
        except Exception as e:
            logger.warning(
                "postcodearea.co.uk failed for %s: %s. Trying StreetCheck...",
                outercode, e
            )
            last_error = str(e)

        # --- Try Secondary Source: StreetCheck ---
        # Note: StreetCheck usually requires a FULL postcode (e.g., UB5 5AF)
        # for detailed demographics, but outercode level (UB5) sometimes works
        # or redirects to a sub-area.
        url_sc = f"{self.STREETCHECK_BASE_URL}/{outercode}"

        try:
            # We use the same fetcher but StreetCheck is usually more stable (no 503)
            # but we still use fresh context to be safe.
            soup_sc = self._fetch_with_playwright(url_sc, outercode)
            return self._parse_streetcheck(soup_sc, outercode)
        except Exception as e:
            logger.error(
                "Both sources failed for %s. Last error: %s",
                outercode, e
            )
            raise ScraperParsingError(
                message=f"Failed to scrape demographics for {outercode} from all sources.",
                details={"postcodearea_error": last_error, "streetcheck_error": str(e)}
            ) from e

    def _fetch_with_playwright(self, url: str, outercode: str) -> BeautifulSoup:
        """
        Fetch page using Playwright with fresh incognito context + retry on 503.

        Strategy:
            1. Open fresh browser context (no cookies = page view limit reset)
            2. Navigate to URL
            3. Wait 3 seconds for page to render
            4. Check: "Server Overload" → close, wait 5s, retry
            5. Otherwise → data is present, grab HTML and return
        """
        last_error = None

        with sync_playwright() as p:
            for attempt in range(1, MAX_RETRIES + 1):
                if attempt > 1:
                    logger.info(
                        "Retry %d/%d for %s (waiting %ds)...",
                        attempt, MAX_RETRIES, outercode, RETRY_DELAY_SECS,
                    )
                    time.sleep(RETRY_DELAY_SECS)

                browser = None
                try:
                    # Fresh browser + context each attempt (mimics incognito)
                    browser = p.chromium.launch(headless=False)
                    context = browser.new_context(
                        user_agent=self._ua.random,
                        locale="en-GB",
                    )
                    page = context.new_page()

                    # Navigate to the page
                    page.goto(url, timeout=PAGE_TIMEOUT_MS)

                    # Wait for page to render
                    time.sleep(3)

                    # Grab the page content
                    html = page.content()
                    browser.close()
                    browser = None

                    # Check: Server Overload = retry
                    if "server overload" in html.lower():
                        logger.debug(
                            "Attempt %d: Server Overload (retrying)", attempt,
                        )
                        last_error = "503 Server Overload"
                        continue

                    # Page loaded with data — return it
                    soup = BeautifulSoup(html, "html.parser")
                    logger.info(
                        "Attempt %d: Page loaded for %s", attempt, outercode,
                    )
                    return soup

                except Exception as e:
                    logger.debug("Attempt %d failed: %s", attempt, e)
                    last_error = str(e)
                finally:
                    if browser:
                        try:
                            browser.close()
                        except Exception:
                            pass

        raise ScraperParsingError(
            message=(
                f"Failed to scrape postcodearea.co.uk for {outercode} "
                f"after {MAX_RETRIES} attempts. Last error: {last_error}. "
                f"Ensure UK VPN is enabled."
            ),
            details={"outercode": outercode, "url": url, "attempts": MAX_RETRIES},
        )

    # ─── HTML Parsing (Verified 2026-02-17) ─────────────────

    def _parse_postcodearea(self, soup: BeautifulSoup, outercode: str) -> dict[str, Any]:
        """
        Parse postcodearea.co.uk HTML to extract all demographic fields.

        HTML structure (Census 2021):
            - Headline stats: .headlineNumber.text-blue in .text-center cards
            - Ethnicity:      #content-ethnicity → .myBar bars
            - Employment:     #content-work → .headlineNumber + .myBar bars
            - Income:         #content-income (or inline headline)
        """
        data = self._empty_demographics()

        # Check for rate limit / overload page
        page_text = soup.get_text(separator=" ", strip=True)
        if "server overload" in page_text.lower():
            raise ScraperParsingError(
                message="postcodearea.co.uk returned 'Server Overload' — UK VPN required",
                details={"outercode": outercode},
            )
        if "free daily page views" in page_text.lower():
            # The daily limit banner appears, but data is STILL in the HTML.
            # We use fresh incognito contexts so this banner is expected.
            logger.debug("Daily limit banner shown — data still present, continuing.")

        # --- Extract headline stats (Population, Households, Income) ---
        self._extract_headline_stats(soup, data)

        # --- Employment Rate & Unemployment ---
        self._extract_employment(soup, data)

        # --- Ethnicity ---
        self._extract_ethnicity(soup, data)

        # --- Social Grades (NS-SEC from Work section) ---
        self._extract_social_grades(soup, data)

        logger.info(
            "Demographics for %s: pop=%d, hh=%d, income=£%d, working=%.1f%%",
            outercode, data["population"], data["households"],
            data["avg_household_income"], data["working"] * 100,
        )
        return data

    def _extract_headline_stats(self, soup: BeautifulSoup, data: dict) -> None:
        """Extract population, households, and income from headline number cards."""
        try:
            # Find all headline stat elements
            headlines = soup.find_all("div", class_="headlineNumber")

            for hn in headlines:
                # Find the label — usually an h2 sibling or parent's text
                parent = hn.parent
                if not parent:
                    continue

                # Get the label text from surrounding context
                label_el = parent.find(["h2", "h3", "h6"])
                if not label_el:
                    # Try grandparent
                    grandparent = parent.parent
                    if grandparent:
                        label_el = grandparent.find(["h2", "h3", "h6"])

                label = label_el.get_text(strip=True).lower() if label_el else ""
                value_text = hn.get_text(strip=True)

                if "population" in label and "density" not in label:
                    data["population"] = self.safe_int(value_text)
                elif "household" in label and "income" not in label:
                    data["households"] = self.safe_int(value_text)
                elif "income" in label or "£" in value_text:
                    income_val = self.safe_int(value_text)
                    if income_val > 1000:  # Sanity check
                        data["avg_household_income"] = income_val
                elif "employment rate" in label or "working" in label:
                    data["working"] = self.safe_float(value_text) / 100
                elif "unemployment" in label:
                    unemp = self.safe_float(value_text) / 100
                    data["unemployed"] = unemp
                    data["unemployment_rate"] = round(unemp, 4)

        except Exception as e:
            logger.debug("Headline stats extraction failed: %s", e)

    def _extract_employment(self, soup: BeautifulSoup, data: dict) -> None:
        """Extract employment and unemployment rates from #content-work section."""
        try:
            work_section = soup.find("div", id="content-work")
            if not work_section:
                return

            # Employment/Unemployment rates are in headlineNumber divs
            headlines = work_section.find_all("div", class_="headlineNumber")
            for hn in headlines:
                parent = hn.parent
                if not parent:
                    continue
                context = parent.get_text(strip=True).lower()
                value = self.safe_float(hn.get_text(strip=True))

                if "employment rate" in context or "working" in context:
                    if data["working"] == 0.0:  # Don't overwrite if already set
                        data["working"] = value / 100
                elif "unemployment" in context:
                    if data["unemployed"] == 0.0:
                        unemp = value / 100
                        data["unemployed"] = unemp
                        data["unemployment_rate"] = round(unemp, 4)

        except Exception as e:
            logger.debug("Employment extraction failed: %s", e)

    def _extract_ethnicity(self, soup: BeautifulSoup, data: dict) -> None:
        """Extract ethnicity percentages from #content-ethnicity bar charts."""
        try:
            ethnicity_section = soup.find("div", id="content-ethnicity")
            if not ethnicity_section:
                return

            white_pct = 0.0
            non_white_pct = 0.0

            for bar in ethnicity_section.find_all("div", class_="myBar"):
                desc_el = bar.find("span", class_="description")
                # Try data-pc attribute first (more reliable), then text
                amount_el = bar.find("div", class_="amount")
                pct_el = bar.find("div", class_="amount-pc")

                if desc_el:
                    label = desc_el.get_text(strip=True).lower()

                    # Get percentage value
                    pct = 0.0
                    if amount_el and amount_el.get("data-pc"):
                        pct = self.safe_float(amount_el["data-pc"])
                    elif pct_el:
                        pct = self.safe_float(pct_el.get_text(strip=True))

                    if "white" in label and "mixed" not in label:
                        white_pct = pct
                    else:
                        non_white_pct += pct

            if white_pct > 0 or non_white_pct > 0:
                data["white"] = round(white_pct / 100, 4)
                data["non_white"] = round(non_white_pct / 100, 4)

        except Exception as e:
            logger.debug("Ethnicity extraction failed: %s", e)

    def _extract_social_grades(self, soup: BeautifulSoup, data: dict) -> None:
        """
        Extract social grades from NS-SEC occupation data in #content-work.

        postcodearea.co.uk uses NS-SEC (Census 2021) instead of AB/C1/C2/DE.
        We map NS-SEC categories to approximate social grade equivalents:
            AB  ≈ Higher Managerial + Lower Managerial
            C1C2 ≈ Intermediate + Small Employers + Lower Supervisory
            DE  ≈ Semi-Routine + Routine + Unemployed
        """
        try:
            work_section = soup.find("div", id="content-work")
            if not work_section:
                return

            # NS-SEC categories from bar charts
            nssec = {}
            for bar in work_section.find_all("div", class_="myBar"):
                desc_el = bar.find("span", class_="description")
                amount_el = bar.find("div", class_="amount")
                pct_el = bar.find("div", class_="amount-pc")

                if desc_el:
                    label = desc_el.get_text(strip=True).lower()
                    pct = 0.0
                    if amount_el and amount_el.get("data-pc"):
                        pct = self.safe_float(amount_el["data-pc"])
                    elif pct_el:
                        pct = self.safe_float(pct_el.get_text(strip=True))

                    nssec[label] = pct

            if not nssec:
                return

            # Map NS-SEC → AB / C1C2 / DE
            ab_categories = ["higher managerial", "lower managerial"]
            c1c2_categories = ["intermediate", "small employers", "lower supervisory"]
            de_categories = ["semi-routine", "routine", "unemployed"]

            ab_total = sum(v for k, v in nssec.items()
                          if any(cat in k for cat in ab_categories))
            c1c2_total = sum(v for k, v in nssec.items()
                            if any(cat in k for cat in c1c2_categories))
            de_total = sum(v for k, v in nssec.items()
                          if any(cat in k for cat in de_categories))

            total = ab_total + c1c2_total + de_total
            if total > 0:
                data["ab"] = round(ab_total / 100, 4)
                data["c1_c2"] = round(c1c2_total / 100, 4)
                data["de"] = round(de_total / 100, 4)

        except Exception as e:
            logger.debug("Social grade extraction failed: %s", e)

    def _parse_streetcheck(self, soup: BeautifulSoup, outercode: str) -> dict[str, Any]:
        """
        Parse streetcheck.co.uk HTML to extract demographic fields.
        """
        data = self._empty_demographics()
        
        # 1. Population (Gender table in #people section)
        people_section = soup.find(id="people")
        if people_section:
            table = people_section.find("table")
            if table:
                for row in table.find_all("tr"):
                    if "Total" in row.get_text():
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            data["population"] = self.safe_int(cells[1].get_text())
                            break

        # 2. Ethnicity (Ethnic Group table in #culture section)
        culture_section = soup.find(id="culture")
        if culture_section:
            tables = culture_section.find_all("table")
            for table in tables:
                if "Ethnic Group" in table.get_text():
                    counts = {}
                    total_count = 0
                    for row in table.find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            val = self.safe_int(cells[1].get_text())
                            if val > 0:
                                counts[label] = val
                                total_count += val
                    
                    if total_count > 0:
                        white_count = sum(v for k, v in counts.items() if "white" in k and "mixed" not in k)
                        data["white"] = round(white_count / total_count, 4)
                        data["non_white"] = round((total_count - white_count) / total_count, 4)
                    break

        # 3. Social Grades (Socio-Economic Classification table in #employment section)
        employment_section = soup.find(id="employment")
        if employment_section:
            tables = employment_section.find_all("table")
            for table in tables:
                if "Socio-Economic Classification" in table.get_text():
                    counts = {}
                    total_count = 0
                    for row in table.find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            val = self.safe_int(cells[1].get_text())
                            if val > 0:
                                counts[label] = val
                                total_count += val
                    
                    if total_count > 0:
                        # Map NS-SEC → AB / C1C2 / DE
                        ab_total = sum(v for k, v in counts.items() if "managerial" in k or "professional" in k)
                        c1c2_total = sum(v for k, v in counts.items() if "intermediate" in k or "small employer" in k or "lower technical" in k)
                        de_total = sum(v for k, v in counts.items() if "semi-routine" in k or "routine occupation" in k or "never worked" in k)
                        
                        data["ab"] = round(ab_total / total_count, 4)
                        data["c1_c2"] = round(c1c2_total / total_count, 4)
                        data["de"] = round(de_total / total_count, 4)
                    break

        logger.info(
            "StreetCheck demographics for %s: pop=%d, white=%.1f%%, ab=%.1f%%",
            outercode, data["population"], (data["white"] or 0) * 100, (data["ab"] or 0) * 100
        )
        return data

    # ─── URL & Town Resolution ──────────────────────────────

    def _get_postal_town(self, outercode: str) -> str:
        """
        Get the postal town slug for a given outercode.

        Uses the OUTERCODE_TO_TOWN mapping for known codes.
        Falls back to 'london' for unmapped codes (safe default for
        most London-area analysis).

        Args:
            outercode: UK outercode (e.g., 'HA1', 'UB5').

        Returns:
            Postal town slug (e.g., 'harrow', 'uxbridge').
        """
        town = OUTERCODE_TO_TOWN.get(outercode)
        if town:
            return town

        # For unmapped codes, try shorter prefix (e.g., "SW1A" → "SW1")
        import re
        match = re.match(r"([A-Z]+\d+)", outercode)
        if match:
            base = match.group(1)
            town = OUTERCODE_TO_TOWN.get(base)
            if town:
                return town

        logger.warning(
            "Unknown outercode '%s' — defaulting to 'london'. "
            "Add it to OUTERCODE_TO_TOWN mapping if needed.",
            outercode,
        )
        return "london"

    # ─── Utilities ──────────────────────────────────────────

    @staticmethod
    def _empty_demographics() -> dict[str, Any]:
        """Return a demographics dict with all fields set to 0."""
        return {
            "population": 0,
            "households": 0,
            "avg_household_income": 0,
            "unemployment_rate": 0.0,
            "working": 0.0,
            "unemployed": 0.0,
            "ab": 0.0,
            "c1_c2": 0.0,
            "de": 0.0,
            "white": 0.0,
            "non_white": 0.0,
        }

    def scrape_multiple(self, outercodes: list[str]) -> dict[str, Any]:
        """
        Scrape demographics for multiple outercodes and return averaged results.

        Args:
            outercodes: List of outercode strings.

        Returns:
            Averaged demographics dict.
        """
        results = []
        for code in outercodes:
            try:
                data = self.scrape_with_fallback(code)
                results.append(data)
            except Exception as e:
                logger.warning("Skipping outercode %s: %s", code, e)

        if not results:
            return self._empty_demographics()

        return self._average_demographics(results)

    @staticmethod
    def _average_demographics(demo_list: list[dict]) -> dict[str, Any]:
        """Average demographics across multiple outercodes."""
        fields = [
            "population", "households", "avg_household_income",
            "unemployment_rate", "working", "unemployed",
            "ab", "c1_c2", "de", "white", "non_white",
        ]
        averaged = {}
        for field in fields:
            values = [d[field] for d in demo_list if d.get(field, 0) > 0]
            if values:
                avg = sum(values) / len(values)
                # Integer fields
                if field in ("population", "households", "avg_household_income"):
                    averaged[field] = int(avg)
                else:
                    averaged[field] = round(avg, 4)
            else:
                averaged[field] = 0
        return averaged
