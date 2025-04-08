import os
import logging
import json
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI, APIError
from datetime import datetime
import web_scraper
from models import db, WatchedShow
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Default categories list (based on serie_tv_viste_da_Luca.txt)
TV_CATEGORIES = [
    "ANIME / ANIMAZIONE", "CRIME / THRILLER", "HORROR / SOPRANNATURALE", 
    "DRAMMATICHE", "FANTASY / SCI-FI", "ALTRE"
]

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # setup a secret key, required by sessions
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SESSION_SECRET") or "a secret key"
    
    # Configure the database - prioritize DATABASE_URL for Render compatibility
    database_url = os.environ.get("DATABASE_URL")
    
    # Postgres on Render requires special handling with psycopg2
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # If no DATABASE_URL set, use SQLite (good for local development)
    if not database_url:
        database_url = "sqlite:///netflix_recommendations.db"
    
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize database with app
    db.init_app(app)
    
    with app.app_context():
        # Create tables
        db.create_all()
    
    # Register routes
    @app.route('/')
    def index():
        """Render the main page with watched shows"""
        # Get all watched shows from database
        watched_shows = WatchedShow.query.all()
        watched_shows_by_category = {}
        
        # Group shows by category
        for category in TV_CATEGORIES:
            watched_shows_by_category[category] = WatchedShow.query.filter_by(category=category).all()
        
        return render_template('index.html', 
                          watched_shows=watched_shows,
                          watched_shows_by_category=watched_shows_by_category,
                          categories=TV_CATEGORIES)

    @app.route('/get_recommendations', methods=['POST'])
    def get_recommendations():
        """Process OpenAI API request for personalized TV show recommendations"""
        try:
            # Get API key from request or environment variable
            api_key = request.json.get('api_key')
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    return jsonify({'error': 'API key è necessaria'}), 400
            
            # Store API key in session for this session only
            session['api_key'] = api_key
            
            # Get all watched shows from database
            watched_shows = WatchedShow.query.all()
            watched_titles = [show.title for show in watched_shows]
            watched_titles_str = ", ".join(watched_titles)
            
            # Initialize OpenAI client
            client = OpenAI(api_key=api_key)
            
            # Create prompt for OpenAI
            try:
                prompt = f"""Considerando le serie TV che ho già visto: {watched_titles_str}, 
                suggeriscimi 5 nuove serie TV disponibili su Netflix Italia che sono uscite di recente 
                e che potrebbero piacermi in base ai miei gusti. 
                Importante: assicurati che siano serie TV che esistono realmente su Netflix Italia,
                possibilmente usando riferimenti da siti come "Netflix Lovers Italia".
                Includi SOLO titoli verificabili e garantisci che le URL delle immagini e delle schede
                siano funzionanti (preferibilmente da TMDB o Netflix/IMDB ufficiali)."""
                
                completion = client.chat.completions.create(
                    model="gpt-4o", # Using the latest model
                    messages=[
                        {"role": "system", "content": f"""Sei un assistente esperto di serie TV che conosce tutti i nuovi rilasci. 
                        Oggi è {datetime.now().strftime("%Y-%m-%d")}. Devi raccomandare SOLO serie TV recenti disponibili su Netflix in Italia.
                        Analizza le preferenze dell'utente basandoti sulle serie TV che ha già visto.
                        Formatta la risposta in JSON con un array 'shows' contenente oggetti con campi:
                        'title': il titolo effettivo della serie TV,
                        'genre': il genere o i generi principali,
                        'description': una breve descrizione della trama,
                        'release_date': la data di uscita su Netflix Italia,
                        'similar_to': elenco di 1-3 serie già viste dall'utente a cui potrebbe essere simile,
                        'image_url': URL ad un'immagine della locandina (usa l'URL reale di Netflix o TMDB),
                        'info_url': URL alla pagina ufficiale Netflix o IMDB della serie TV."""},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                response = completion.choices[0].message.content
                # Parse the JSON response to ensure it's valid
                recommendations = json.loads(response)
                
                # Process recommendations using our web scraper to verify and enhance data
                logger.info("Processing recommendations with web_scraper...")
                processed_response = web_scraper.process_openai_recommendations(response)
                
                return jsonify({
                    'response': processed_response,
                    'watched_count': len(watched_titles)
                })
                
            except APIError as e:
                logger.error(f"OpenAI API error: {str(e)}")
                return jsonify({'error': f'OpenAI API error: {str(e)}'}), 500
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                return jsonify({'error': f'Errore nel formato della risposta: {str(e)}'}), 500
            except Exception as e:
                logger.error(f"Error calling OpenAI: {str(e)}")
                return jsonify({'error': f'Errore: {str(e)}'}), 500
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'error': f'Errore imprevisto: {str(e)}'}), 500

    @app.route('/watched_shows', methods=['GET'])
    def get_watched_shows():
        """Get all watched shows"""
        try:
            watched_shows = WatchedShow.query.all()
            return jsonify({
                'shows': [show.to_dict() for show in watched_shows]
            })
        except Exception as e:
            logger.error(f"Error getting watched shows: {str(e)}")
            return jsonify({'error': f'Errore: {str(e)}'}), 500

    @app.route('/watched_shows', methods=['POST'])
    def add_watched_show():
        """Add a new watched show"""
        try:
            data = request.json
            title = data.get('title')
            category = data.get('category')
            
            if not title:
                return jsonify({'error': 'Il titolo è necessario'}), 400
            
            # Check if show already exists
            existing_show = WatchedShow.query.filter_by(title=title).first()
            if existing_show:
                return jsonify({'error': f'La serie TV "{title}" è già nella tua lista'}), 400
            
            new_show = WatchedShow(
                title=title,
                category=category
            )
            db.session.add(new_show)
            db.session.commit()
            
            return jsonify({
                'message': f'Serie TV "{title}" aggiunta con successo',
                'show': new_show.to_dict()
            })
        except Exception as e:
            logger.error(f"Error adding watched show: {str(e)}")
            return jsonify({'error': f'Errore: {str(e)}'}), 500

    @app.route('/watched_shows/<int:id>', methods=['DELETE'])
    def delete_watched_show(id):
        """Delete a watched show"""
        try:
            show = WatchedShow.query.get(id)
            if not show:
                return jsonify({'error': 'Serie TV non trovata'}), 404
            
            db.session.delete(show)
            db.session.commit()
            
            return jsonify({
                'message': f'Serie TV "{show.title}" rimossa con successo'
            })
        except Exception as e:
            logger.error(f"Error deleting watched show: {str(e)}")
            return jsonify({'error': f'Errore: {str(e)}'}), 500
    
    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG", "True").lower() == "true")