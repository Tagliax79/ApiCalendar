import os
import re
import logging
from app import create_app, db, WatchedShow

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_file_and_import(file_path):
    """Parse TV shows from file and import to database"""
    logger.info(f"Reading TV shows from: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Split by category
        categories = re.split(r'\n([A-Z /]+):\n', content)
        
        # First item is empty, skip it
        categories = categories[1:]
        
        # Process each category
        app = create_app()
        with app.app_context():
            # First, check and clear existing data if necessary
            existing_count = db.session.query(WatchedShow).count()
            if existing_count > 0:
                logger.info(f"Found {existing_count} existing show records in database")
                logger.info("Clearing existing data before reimporting...")
                db.session.query(WatchedShow).delete()
                db.session.commit()
            
            total_imported = 0
            
            for i in range(0, len(categories), 2):
                if i+1 < len(categories):
                    category_name = categories[i].strip()
                    shows_text = categories[i+1]
                    
                    # Extract show titles
                    show_titles = re.findall(r'- (.*?)$', shows_text, re.MULTILINE)
                    
                    for title in show_titles:
                        title_stripped = title.strip()
                        if title_stripped:  # Skip empty titles
                            show = WatchedShow(
                                title=title_stripped,
                                category=category_name
                            )
                            db.session.add(show)
                            total_imported += 1
                    
                    logger.info(f"Imported {len(show_titles)} shows from category {category_name}")
                    
            db.session.commit()
            logger.info(f"Import completed successfully! Total shows imported: {total_imported}")
            
    except Exception as e:
        logger.error(f"Error importing shows: {str(e)}")
        raise

if __name__ == "__main__":
    # Import from the file
    parse_file_and_import('attached_assets/serie_tv_viste_da_Luca.txt')