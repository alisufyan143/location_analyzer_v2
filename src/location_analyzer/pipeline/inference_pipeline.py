import logging
from typing import Dict, Any

from location_analyzer.scrapers.streetcheck import DemographicsScraper
from location_analyzer.scrapers.crystalroof import CrystalRoofScraper

logger = logging.getLogger(__name__)

class InferencePipeline:
    """Orchestrates Phase 3 Scraping to gather live data for Phase 4 ML Inference."""
    
    def __init__(self):
        # Initialize scrapers
        self.demo_scraper = DemographicsScraper()
        self.cr_scraper = CrystalRoofScraper()
        
    def _get_outercode(self, postcode: str) -> str:
        """Extracts the outercode from a standard UK format postcode."""
        return postcode.strip().split()[0].upper()

    def run(self, postcode: str) -> Dict[str, Any]:
        """
        Executes the scraping pipeline for a given postcode and formats the 
        output dictionary into the exact schema expected by XGBoost `PredictionService`.
        """
        logger.info(f"Starting Inference Pipeline for Postcode: {postcode}")
        
        outercode = self._get_outercode(postcode)
        
        # 1. Scrape StreetCheck / PostcodeArea for Demographics
        try:
            demo_data = self.demo_scraper.scrape(outercode)
            logger.info(f"Demographics scraped: {demo_data}")
        except Exception as e:
            logger.error(f"Failed to scrape demographics for {outercode}: {e}")
            demo_data = {}

        # 2. Scrape CrystalRoof for Transport/Amenities
        try:
            cr_data = self.cr_scraper.scrape(postcode)
            logger.info(f"CrystalRoof scraped: {cr_data}")
        except Exception as e:
            logger.error(f"Failed to scrape CrystalRoof for {postcode}: {e}")
            cr_data = {}

        # 3. Combine dictionary into the unified format
        combined = {}
        combined.update(demo_data)
        combined.update(cr_data)
        
        # Map Scraper keys to XGBoost expected feature columns
        if 'c1_c2' in combined:
            combined['c1/c2'] = combined.pop('c1_c2')
        if 'non_white' in combined:
            combined['non-white'] = combined.pop('non_white')
            
        # Add basic identifiers
        combined['postcode'] = postcode
        combined['outercode'] = outercode
        
        return combined

