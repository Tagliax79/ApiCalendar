import trafilatura
import json
import re
import logging
from urllib.parse import quote
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)

def sanitize_title(title):
    """Sanitize title for URL usage"""
    # Remove special characters and replace spaces with dashes
    return re.sub(r'[^a-zA-Z0-9\s-]', '', title).strip().replace(' ', '-').lower()

def get_netflix_lovers_data(title):
    """
    Cerca informazioni su una serie TV su Netflix Lovers Italia.
    Restituisce un dizionario con i dati disponibili o None se non trovata.
    """
    try:
        # Sanitize the title for the URL
        safe_title = quote(sanitize_title(title))
        
        # Construct the URL for Netflix Lovers search
        search_url = f"https://www.netflixlovers.it/?s={safe_title}"
        logger.info(f"Searching Netflix Lovers for: {title} at URL: {search_url}")
        
        # Get the search results page using requests
        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Parse the HTML content with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for search results
            articles = soup.find_all('article')
            
            if not articles:
                logger.warning(f"No search results found for: {title}")
                return None
                
            # Get the first result
            first_article = articles[0]
            
            # Extract the link and title
            link_elem = first_article.find('a')
            if not link_elem:
                return None
                
            article_url = link_elem.get('href')
            article_title = link_elem.get('title') or link_elem.text.strip()
            
            # Try to find an image
            img_elem = first_article.find('img')
            img_url = img_elem.get('src') if img_elem else None
            
            # Get more details from the article
            try:
                article_response = requests.get(article_url, timeout=10)
                article_soup = BeautifulSoup(article_response.text, 'html.parser')
                
                # Try to extract a description
                content_div = article_soup.find('div', class_='entry-content')
                description = ""
                if content_div:
                    paragraphs = content_div.find_all('p')
                    if paragraphs:
                        # Get the first two paragraphs for the description
                        description = " ".join([p.text.strip() for p in paragraphs[:2]])
            except:
                description = ""
            
            return {
                "title": article_title or title,
                "found": True,
                "source": "Netflix Lovers Italia",
                "search_url": search_url,
                "article_url": article_url,
                "img_url": img_url,
                "description": description
            }
            
        except Exception as req_e:
            logger.error(f"Error fetching search results: {str(req_e)}")
            # Fallback to trafilatura if requests fails
            search_content = trafilatura.fetch_url(search_url)
            if not search_content:
                logger.warning(f"No content found for search: {title}")
                return None
                
            # Extract the text content
            search_text = trafilatura.extract(search_content)
            
            # If no results found
            if "Nessun risultato" in search_text or not search_text:
                logger.warning(f"No search results found for: {title}")
                return None
                
            # Return basic data with search URL
            return {
                "title": title,
                "found": True,
                "source": "Netflix Lovers Italia",
                "search_url": search_url,
                "article_url": search_url
            }
        
    except Exception as e:
        logger.error(f"Error searching for {title}: {str(e)}")
        return None

def get_netflix_url(title):
    """
    Genera un URL per Netflix basato sul titolo.
    Non garantisce che l'URL sia valido, ma fornisce un formato plausibile.
    """
    safe_title = sanitize_title(title)
    return f"https://www.netflix.com/it/title/search?q={quote(title)}"

def get_justwatch_url(title):
    """
    Genera un URL per JustWatch basato sul titolo.
    JustWatch è un aggregatore che mostra dove vedere i film/serie legalmente.
    """
    safe_title = sanitize_title(title)
    return f"https://www.justwatch.com/it/cerca?q={quote(title)}"

def get_tmdb_image_url(title):
    """
    Genera un URL per un'immagine di TMDB basato sul titolo.
    Questo è solo un esempio e non garantisce che l'URL sia valido.
    In un'implementazione reale, useremmo l'API di TMDB.
    """
    return f"https://image.tmdb.org/t/p/w500/search?q={quote(title)}"

def verify_netflix_show(title):
    """
    Verifica se una serie TV esiste effettivamente su Netflix Italia.
    Restituisce informazioni sulla serie se trovata, altrimenti None.
    """
    # Per ora utilizziamo Netflix Lovers Italia come fonte
    result = get_netflix_lovers_data(title)
    if result and result.get("found"):
        return result
    return None

def enrich_show_data(show_data):
    """
    Arricchisce i dati di una serie TV con informazioni verificate.
    Modifica le URL di immagini e informa e verifica l'esistenza.
    """
    try:
        title = show_data.get("title", "")
        if not title:
            return show_data
            
        # Verifica l'esistenza su Netflix Italia
        verified_data = verify_netflix_show(title)
        
        # Se non verificata, manteniamo i dati originali ma aggiungiamo un flag
        if not verified_data:
            show_data["verified"] = False
            # Aggiungiamo un URL a JustWatch come alternativa
            show_data["info_url"] = get_justwatch_url(title)
            return show_data
            
        # Se verificata, aggiorniamo i dati con informazioni più affidabili
        show_data["verified"] = True
        
        # Usa l'URL dell'articolo di Netflix Lovers come fonte principale
        article_url = verified_data.get("article_url")
        if article_url:
            show_data["info_url"] = article_url
            
        # Aggiorna anche la descrizione se disponibile
        description = verified_data.get("description")
        if description and len(description) > 10:
            show_data["verified_description"] = description
            
        # Aggiorna l'URL dell'immagine se disponibile
        img_url = verified_data.get("img_url")
        if img_url and img_url.startswith("http"):
            show_data["verified_image_url"] = img_url
        
        return show_data
        
    except Exception as e:
        logger.error(f"Error enriching show data: {str(e)}")
        return show_data

def process_openai_recommendations(recommendations_json):
    """
    Processa le raccomandazioni di OpenAI verificando e arricchendo i dati.
    """
    try:
        data = json.loads(recommendations_json)
        shows = data.get("shows", [])
        
        enriched_shows = []
        for show in shows:
            enriched_show = enrich_show_data(show)
            enriched_shows.append(enriched_show)
            
        data["shows"] = enriched_shows
        return json.dumps(data)
        
    except Exception as e:
        logger.error(f"Error processing recommendations: {str(e)}")
        return recommendations_json  # Return original in case of error