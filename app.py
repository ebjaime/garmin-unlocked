from flask import Flask, render_template, jsonify, session, request, redirect, url_for
import os
import json
from datetime import datetime, timedelta
from main import GarminWrapped
import secrets
from storage import save_to_storage, load_from_storage, delete_from_storage
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get or create a persistent secret key
def get_secret_key():
    secret_file = '.secret_key'
    if os.path.exists(secret_file):
        with open(secret_file, 'r') as f:
            return f.read().strip()
    else:
        key = secrets.token_hex(32)
        with open(secret_file, 'w') as f:
            f.write(key)
        return key

# Configure Gemini AI
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def markdown_to_html(text):
    """Convert markdown formatting to HTML."""
    import re
    
    # Convert **bold** to <strong> using regex
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    
    # Convert bullet points
    lines = text.split('\n')
    result = []
    for line in lines:
        line = line.strip()
        if line.startswith('• '):
            result.append(line)
        elif line.startswith('* '):
            result.append('• ' + line[2:])
        elif line.startswith('- '):
            result.append('• ' + line[2:])
        elif line:
            result.append(line)
    
    return '<br>'.join(result)

def generate_ai_insights(wrapped_data):
    """Generate personalized insights using Gemini AI."""
    if not GEMINI_API_KEY:
        return "AI insights unavailable. Set GEMINI_API_KEY environment variable."
    
    try:
        # Prepare summary of user's data
        activities = wrapped_data.get('activities', {})
        sleep = wrapped_data.get('sleep', {})
        vo2 = wrapped_data.get('vo2_max', {})
        stress = wrapped_data.get('stress', {})
        
        prompt = f"""Analyze this runner's 2025 data. Talk directly to the user. Provide up to 5 bullet points (max 150 words total). Use markdown **bold** for key metrics.

Data: {activities.get('total_runs', 0)} runs, {activities.get('total_distance_km', 0):.0f}km, {activities.get('avg_pace_formatted', 'N/A')} avg pace, {activities.get('total_time_hours', 0):.1f}h total, {activities.get('total_distance_km', 0) / max(activities.get('total_runs', 1), 1):.1f}km/run avg, VO2 {vo2.get('latest_vo2_max', 'N/A')}, sleep {sleep.get('avg_sleep_hours', 0):.1f}h, stress {stress.get('avg_stress_level', 0):.0f}/100

Format:
• [Insight with **number** highlighted]
• [Insight with **metric** highlighted]
• [Insight with **stat** highlighted]
• [Insight with about the percentile of fitness or running level, if applicable]


Be concise, analytical, data-focused."""
        
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        return markdown_to_html(response.text)
    except Exception as e:
        error_msg = str(e).lower()
        print(f"Error generating insights: {e}")
        
        # Handle rate limit errors specifically
        if 'quota' in error_msg or 'rate limit' in error_msg or '429' in error_msg:
            return "You've reached the Gemini API rate limit. Your insights will be available shortly. Try refreshing in a few minutes!"
        elif 'resource exhausted' in error_msg:
            return "Gemini API quota exceeded for today. Check back tomorrow for AI-powered insights!"
        elif 'api key' in error_msg or 'authentication' in error_msg:
            return "API key issue detected. Please check your Gemini API key configuration."
        else:
            return "Your dedication this year has been remarkable! Every run, every step forward matters."

def generate_ai_forecast(wrapped_data, ai_insights):
    """Generate next year recommendations using Gemini AI."""
    if not GEMINI_API_KEY:
        return "AI forecast unavailable. Set GEMINI_API_KEY environment variable."
    
    try:
        activities = wrapped_data.get('activities', {})
        sleep = wrapped_data.get('sleep', {})
        vo2 = wrapped_data.get('vo2_max', {})
        records = activities.get('personal_records', {})
        
        prompt = f"""Create up to 5 specific 2026 goals (max 150 words total). Talk directly to the user. Use markdown **bold** for target numbers.

2025: {activities.get('total_runs', 0)} runs, {activities.get('total_distance_km', 0):.0f}km, {activities.get('avg_pace_formatted', 'N/A')} pace, {activities.get('total_distance_km', 0) / max(activities.get('total_runs', 1), 1):.1f}km/run, VO2 {vo2.get('latest_vo2_max', 'N/A')}, 5K {records.get('5k', {}).get('pace_formatted', 'N/A') if records.get('5k') else 'N/A'}, 10K {records.get('10k', {}).get('pace_formatted', 'N/A') if records.get('10k') else 'N/A'}, sleep {sleep.get('avg_sleep_hours', 0):.1f}h

These were the insights from 2025 that you generated:
{ai_insights}

Format:
• [Volume goal with **target number** (always per month or per week)]
• [Pace goal with **target time** (always for a focused distance)]
• [Improvement training goal with **specific metric** (weekly or monthly mileage target, long run distance, etc.)]
• [Health goal with **specific metric** (sleep hours, HR, etc.)]
• [Other...]

Calculate 10-20% improvements. Be specific."""
        
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        return markdown_to_html(response.text)
    except Exception as e:
        error_msg = str(e).lower()
        print(f"Error generating forecast: {e}")
        
        # Handle rate limit errors specifically
        if 'quota' in error_msg or 'rate limit' in error_msg or '429' in error_msg:
            return "Rate limit reached. Your personalized 2026 goals will be available after a short break!"
        elif 'resource exhausted' in error_msg:
            return "Daily quota exceeded. Check back tomorrow for your AI-powered 2026 forecast!"
        elif 'api key' in error_msg or 'authentication' in error_msg:
            return "API authentication error. Please verify your Gemini API key."
        else:
            return "In 2026, challenge yourself to go further. Set a new PR, explore new routes, keep growing!"

app = Flask(__name__)
# Configure secret key for sessions (persistent across restarts)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', get_secret_key())
# Increase timeout for long requests
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# Session configuration
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'garmin_wrapped_session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Store wrapped data globally (in production, use sessions or cache)
wrapped_data = None

# Ensure users and insights directories exist (for local development)
os.makedirs('users', exist_ok=True)
os.makedirs('insights', exist_ok=True)

def save_insights(email, insights, forecast):
    """Save AI insights using storage backend (GCS or local)."""
    from storage import save_insights_to_storage
    data = {
        'insights': insights,
        'forecast': forecast,
        'generated_at': datetime.now().isoformat()
    }
    return save_insights_to_storage(email, data)

def load_insights(email):
    """Load cached AI insights from storage backend (GCS or local)."""
    from storage import load_insights_from_storage
    return load_insights_from_storage(email)

def get_user_filename(email):
    """Generate filename from email."""
    # Extract username from email (before @)
    username = email.split('@')[0].replace('.', '_')
    return os.path.join('users', f"{username}_wrapped_2025.json")

def save_wrapped_data(email, data):
    """Save wrapped data using storage backend."""
    return save_to_storage(email, data)

def load_wrapped_data(email):
    """Load wrapped data using storage backend."""
    return load_from_storage(email)

@app.route('/')
def index():
    # Check if user is logged in
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login')
def login():
    # If already logged in, redirect to main page
    if 'email' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle login request."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    remember = data.get('remember', False)
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    try:
        # Test the credentials by authenticating with Garmin
        test_garmin = GarminWrapped(email=email, password=password)
        
        # Actually authenticate to verify credentials
        if not test_garmin.authenticate():
            return jsonify({"error": "Wrong password"}), 401
        
        del test_garmin  # Clean up after validation
        
        # If successful, store in session
        session.permanent = remember  # Set this BEFORE storing data
        session['email'] = email
        session['password'] = password  # In production, use encrypted storage
        session.modified = True  # Force session to save
        
        return jsonify({"success": True, "message": "Login successful"}), 200
    except Exception as e:
        error_message = str(e).lower()
        # Check for authentication-specific errors
        if 'authentication' in error_message or 'login' in error_message or 'credentials' in error_message or 'password' in error_message or 'unauthorized' in error_message:
            return jsonify({"error": "Wrong password"}), 401
        return jsonify({"error": f"Login failed: {str(e)}"}), 401

@app.route('/api/check-activities', methods=['GET'])
def check_activities():
    """Check what activity types the user has in their Garmin data."""
    email = session.get('email')
    password = session.get('password')
    
    if not email or not password:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        # Quick check to see what activities exist
        garmin = GarminWrapped(email, password)
        if not garmin.authenticate():
            return jsonify({"error": "Authentication failed"}), 401
        
        # Get all activities for 2025
        all_activities = garmin.client.get_activities_by_date("2025-01-01", "2025-12-31")
        
        # Count activity types
        activity_counts = {}
        for activity in all_activities:
            activity_type_key = activity.get('activityType', {}).get('typeKey', '').lower()
            
            # Map to our categories
            if 'running' in activity_type_key or 'run' in activity_type_key:
                activity_counts['running'] = activity_counts.get('running', 0) + 1
            elif 'cycling' in activity_type_key or 'biking' in activity_type_key or 'bike' in activity_type_key:
                activity_counts['cycling'] = activity_counts.get('cycling', 0) + 1
            elif 'swimming' in activity_type_key or 'swim' in activity_type_key:
                activity_counts['swimming'] = activity_counts.get('swimming', 0) + 1
            else:
                activity_counts['others'] = activity_counts.get('others', 0) + 1
        
        return jsonify({"available_activities": activity_counts}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Handle logout request."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200

@app.route('/api/format-stories', methods=['GET'])
def format_stories_endpoint():
    """Format stories using cached data with user's selected unit and activities."""
    email = session.get('email')
    if not email:
        return jsonify({"error": "Not logged in"}), 401
    
    # Get user preferences from query parameters
    unit = request.args.get('unit', 'km')
    activities_param = request.args.get('activities', '["running"]')
    
    try:
        selected_activities = json.loads(activities_param)
    except:
        selected_activities = ['running']
    
    print(f"\n=== FORMAT STORIES ENDPOINT ===")
    print(f"Received unit: {unit}")
    print(f"Received activities param: {activities_param}")
    print(f"Parsed activities: {selected_activities}")
    
    # Load cached wrapped data
    wrapped_data = load_wrapped_data(email)
    
    if not wrapped_data:
        return jsonify({"error": "No cached data available. Please refresh the page."}), 404
    
    # Format stories with user's preferences
    stories = format_stories(wrapped_data, email, unit, selected_activities)
    
    print(f"Generated {len(stories)} stories")
    story_titles = [s.get('title', 'NO_TITLE') for s in stories]
    print(f"Story titles: {story_titles}")
    print("=== END FORMAT STORIES ===\n")
    
    return jsonify({"stories": stories}), 200

@app.route('/api/generate-wrapped', methods=['GET'])
def generate_wrapped():
    """Stream progress updates during wrapped generation using Server-Sent Events."""
    from flask import Response
    import json
    import queue
    import threading
    
    # Get credentials from session BEFORE entering generator
    email = session.get('email')
    password = session.get('password')
    
    # Get user preferences from query parameters
    unit = request.args.get('unit', 'km')
    activities_param = request.args.get('activities', '["running"]')
    
    try:
        selected_activities = json.loads(activities_param)
    except:
        selected_activities = ['running']
    
    print(f"DEBUG: Received unit: {unit}, activities: {selected_activities}")
    
    # Check if preferences changed from cached version
    cached_data = load_wrapped_data(email)
    if cached_data:
        # If activity_types is missing, this is old cache format - regenerate
        if 'activity_types' not in cached_data:
            print(f"DEBUG: Old cache format detected (missing activity_types), clearing cache")
            delete_from_storage(email)
            cached_data = None
        else:
            cached_activities = cached_data.get('activity_types', ['running'])
            if set(selected_activities) != set(cached_activities):
                print(f"DEBUG: Activity preferences changed from {cached_activities} to {selected_activities}, clearing cache")
                delete_from_storage(email)
                cached_data = None
    
    # Store preferences in session for later use
    session['unit'] = unit
    session['selected_activities'] = selected_activities
    
    if not email or not password:
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': 'Not logged in'})}\n\n",
            mimetype='text/event-stream'
        )
    
    def generate():
        global wrapped_data
        
        # Use values from outer scope (already captured from session/request)
        user_email = email
        user_password = password
        user_unit = unit
        user_activities = selected_activities
        
        # Create a queue to communicate between threads
        message_queue = queue.Queue()
        
        def progress_callback(message):
            # Put message in queue
            message_queue.put(message)
        
        def run_wrapped_generation():
            try:
                # Use values captured from outer scope
                
                # Try to load cached data first
                print("Thread: Checking for cached data...")
                cached_data = load_wrapped_data(user_email)
                
                if cached_data:
                    print("Thread: Using cached data")
                    progress_callback("Loading your saved Wrapped data...")
                    message_queue.put(('COMPLETE', cached_data))
                    return
                
                print("Thread: No cache found, starting Garmin initialization...")
                # Initialize Garmin
                garmin = GarminWrapped(
                    email=user_email,
                    password=user_password
                )
                
                print("Thread: Calling generate_wrapped_2025...")
                # Generate with progress callback
                global wrapped_data
                
                print(f"Thread: Fetching activities: {user_activities}")
                
                wrapped_data = garmin.generate_wrapped_2025(
                    progress_callback=progress_callback,
                    activity_types=user_activities
                )
                
                # Save the generated data
                print("Thread: Saving wrapped data to file...")
                save_wrapped_data(user_email, wrapped_data)
                
                print("Thread: Generation complete, sending COMPLETE signal")
                # Signal completion
                message_queue.put(('COMPLETE', wrapped_data))
            except Exception as e:
                print(f"Thread: Error occurred: {e}")
                message_queue.put(('ERROR', str(e)))
        
        try:
            # Send initial message
            print("Main: Sending initial message")
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Connecting to Garmin...'})}\n\n"
            
            # Start wrapped generation in a separate thread
            print("Main: Starting background thread")
            thread = threading.Thread(target=run_wrapped_generation)
            thread.daemon = True
            thread.start()
            
            # Stream messages from the queue
            print("Main: Starting to read from queue")
            while True:
                msg = message_queue.get()
                print(f"Main: Got message from queue: {msg}")
                
                if isinstance(msg, tuple):
                    if msg[0] == 'COMPLETE':
                        print("Main: Received COMPLETE signal")
                        wrapped_data = msg[1]
                        break
                    elif msg[0] == 'ERROR':
                        print(f"Main: Received ERROR signal: {msg[1]}")
                        yield f"data: {json.dumps({'type': 'error', 'message': msg[1]})}\n\n"
                        return
                else:
                    # Progress message
                    print(f"Main: Yielding progress message: {msg}")
                    yield f"data: {json.dumps({'type': 'progress', 'message': msg})}\n\n"
            
            print("Main: Waiting for thread to finish")
            thread.join(timeout=5)
            
            if "error" in wrapped_data:
                yield f"data: {json.dumps({'type': 'error', 'message': wrapped_data['error']})}\n\n"
                return
            
            # Format data for stories (pass preferences captured earlier)
            print(f"DEBUG format_stories: activity_types={user_activities}")
            print(f"DEBUG format_stories: activities_by_type keys={list(wrapped_data.get('activities_by_type', {}).keys())}")
            if 'cycling' in wrapped_data.get('activities_by_type', {}):
                print(f"DEBUG format_stories: cycling data exists with {wrapped_data['activities_by_type']['cycling'].get('total_runs', 0)} activities")
            stories = format_stories(wrapped_data, user_email, user_unit, user_activities)
            
            # Send completion with data and wrapped_data for activity checking
            yield f"data: {json.dumps({'type': 'complete', 'stories': stories, 'wrapped_data': wrapped_data})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })

@app.route('/api/wrapped-data', methods=['GET'])
def get_wrapped_data():
    if not wrapped_data or "error" in wrapped_data:
        return jsonify({"error": "No data available"}), 404
    
    email = session.get('email')
    unit = session.get('unit', 'km')
    activity_types = session.get('selected_activities', ['running'])
    stories = format_stories(wrapped_data, email, unit, activity_types)
    return jsonify(stories)

@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    """Delete cached data and insights to force regeneration."""
    if 'email' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    email = session.get('email')
    
    try:
        from storage import delete_insights_from_storage
        
        # Delete both wrapped data and insights
        data_deleted = delete_from_storage(email)
        insights_deleted = delete_insights_from_storage(email)
        
        if data_deleted or insights_deleted:
            return jsonify({"message": "Cache cleared (data and insights)"}), 200
        else:
            return jsonify({"message": "No cache found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def format_stories(wrapped, email=None, unit='km', activity_types=None):
    """Format wrapped data into story slides.
    
    Args:
        wrapped: The wrapped data dictionary
        email: User email for caching insights
        unit: Distance unit preference ('km' or 'miles')
        activity_types: List of selected activity types
    """
    stories = []
    
    # Set defaults
    if activity_types is None:
        activity_types = wrapped.get('activity_types', ['running'])
    
    unit_label = 'mi' if unit == 'miles' else 'km'
    
    def convert_distance(km):
        """Convert distance based on unit preference."""
        if unit == 'miles':
            return km * 0.621371
        return km
    
    def convert_pace(pace_min_km):
        """Convert pace from min/km to min/mile if needed.
        
        Args:
            pace_min_km: Pace in minutes per kilometer (float)
            
        Returns:
            Formatted pace string (e.g., "5:30")
        """
        if unit == 'miles':
            # Convert min/km to min/mile: multiply by 1.60934
            pace_min_mile = pace_min_km * 1.60934
            minutes = int(pace_min_mile)
            seconds = int((pace_min_mile - minutes) * 60)
            return f"{minutes}:{seconds:02d}"
        else:
            # Already in min/km, just format
            minutes = int(pace_min_km)
            seconds = int((pace_min_km - minutes) * 60)
            return f"{minutes}:{seconds:02d}"
    
    # Story 1: Running Summary (main activity is always running-focused)
    if wrapped.get("activities"):
        activities = wrapped["activities"]
        total_distance = convert_distance(activities.get('total_distance_km', 0))
        
        stories.append({
            "type": "running_summary",
            "title": "Running",
            "emoji": "🏃",
            "stats": [
                {"label": "Total Runs", "value": activities.get('total_runs', 0)},
                {"label": "Distance", "value": f"{total_distance:.2f} {unit_label}"},
                {"label": "Time", "value": f"{activities.get('total_time_hours', 0):.2f} hours"},
                {"label": "Calories", "value": f"{activities.get('total_calories', 0):,}"}
            ]
        })
        
        # Story 3: Longest Run
        if activities.get('longest_run'):
            longest = activities['longest_run']
            longest_distance = convert_distance(longest['distance_km'])
            stories.append({
                "type": "highlight",
                "title": "Longest Run",
                "emoji": "🏆",
                "main_stat": f"{longest_distance:.2f} {unit_label}",
                "date": longest.get('date', '').split('T')[0] if longest.get('date') else '',
                "secondary": f"{longest['duration_minutes']:.0f} minutes"
            })
        
        # Story 4: Monthly Comparison (moved here after longest run)
        if activities.get('monthly_stats'):
            monthly_stats = activities['monthly_stats']
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            # Get PR dates to mark months with PRs
            pr_months = {}
            if activities.get('personal_records'):
                pr_records = activities['personal_records']
                distance_labels = {
                    "5k": "5K",
                    "10k": "10K",
                    "half_marathon": "HM",
                    "marathon": "M"
                }
                for distance, record in pr_records.items():
                    if record and record.get('date'):
                        date_str = record['date']
                        try:
                            if 'T' in date_str:
                                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            elif ' ' in date_str:
                                date = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                            else:
                                date = datetime.strptime(date_str, "%Y-%m-%d")
                            month_key = date.strftime("%Y-%m")
                            if month_key not in pr_months:
                                pr_months[month_key] = []
                            pr_months[month_key].append(distance_labels[distance])
                        except:
                            pass
            
            months_data = []
            for i in range(1, 13):
                month_key = f"2025-{i:02d}"
                if month_key in monthly_stats:
                    stat = monthly_stats[month_key]
                    month_distance = convert_distance(stat['total_distance_km'])
                    # Convert pace if needed
                    pace_min_km = stat.get('avg_pace_min_km', 0)
                    pace_formatted = convert_pace(pace_min_km) if pace_min_km > 0 else '0:00'
                    months_data.append({
                        "name": month_names[i-1],
                        "distance": f"{month_distance:.0f}",
                        "runs": stat['count'],
                        "pace": pace_formatted,
                        "prs": pr_months.get(month_key, [])
                    })
                else:
                    months_data.append({
                        "name": month_names[i-1],
                        "distance": "0",
                        "runs": 0,
                        "pace": "0:00",
                        "prs": []
                    })
            
            # Only add if there's any data
            if any(m['distance'] != '0' for m in months_data):
                stories.append({
                    "type": "monthly_grid",
                    "title": "Month by Month",
                    "emoji": "📈",
                    "months": months_data,
                    "unit": unit_label
                })
        
        # Story 5: Fastest Pace
        if activities.get('fastest_pace'):
            fastest = activities['fastest_pace']
            fastest_distance = convert_distance(fastest['distance_km'])
            # Convert pace to correct unit
            pace_min_km = fastest.get('pace_min_km', 0)
            pace_formatted = convert_pace(pace_min_km) if pace_min_km > 0 else fastest.get('pace_formatted', '0:00')
            stories.append({
                "type": "highlight",
                "title": "Fastest Pace",
                "emoji": "⚡",
                "main_stat": pace_formatted + f"/{unit_label}",
                "date": fastest.get('date', '').split('T')[0] if fastest.get('date') else '',
                "secondary": f"{fastest_distance:.2f} {unit_label} run"
            })
        
        # Story 6: Averages
        if activities.get('averages'):
            avg = activities['averages']
            avg_distance = convert_distance(avg['distance_km'])
            # Convert pace to correct unit
            pace_min_km = avg.get('pace_min_km', 0)
            pace_formatted = convert_pace(pace_min_km) if pace_min_km > 0 else avg.get('pace_formatted', '0:00')
            stories.append({
                "type": "stats",
                "title": "Your Averages",
                "emoji": "📊",
                "stats": [
                    {"label": "Distance", "value": f"{avg_distance:.2f} {unit_label}"},
                    {"label": "Pace", "value": pace_formatted + f"/{unit_label}"},
                    {"label": "Duration", "value": f"{avg['duration_minutes']:.0f} min"},
                    {"label": "Heart Rate", "value": f"{avg['heart_rate_bpm']:.0f} bpm"} if avg.get('heart_rate_bpm') else None
                ]
            })
        
        # Story 7: Locations
        if activities.get('countries') and activities['countries'].get('total_countries', 0) > 0:
            countries_data = activities['countries']
            total_countries = countries_data['total_countries']
            country_list = countries_data.get('unique_countries', [])
            
            stories.append({
                "type": "countries",
                "title": "Places You've Run",
                "emoji": "📍",
                "total_countries": total_countries,
                "countries": country_list,
                "main_stat": f"{total_countries} " + ("Location" if total_countries == 1 else "Locations")
            })
    
    # Story 8: Sleep
    if wrapped.get("sleep"):
        sleep = wrapped["sleep"]
        sleep_stats = []
        if 'avg_sleep_score' in sleep:
            sleep_stats.append({"label": "Sleep Score", "value": f"{sleep['avg_sleep_score']}/100"})
        if 'avg_sleep_hours' in sleep:
            sleep_stats.append({"label": "Avg Sleep", "value": f"{sleep['avg_sleep_hours']}h/night"})
        if 'avg_deep_sleep_hours' in sleep:
            sleep_stats.append({"label": "Deep Sleep", "value": f"{sleep['avg_deep_sleep_hours']}h"})
        if 'avg_rem_sleep_hours' in sleep:
            sleep_stats.append({"label": "REM Sleep", "value": f"{sleep['avg_rem_sleep_hours']}h"})
        
        if sleep_stats:
            stories.append({
                "type": "stats",
                "title": "Sleep",
                "emoji": "😴",
                "stats": sleep_stats
            })
    
    # Story 9: Heart Rate
    if wrapped.get("heart_rate"):
        hr = wrapped["heart_rate"]
        if 'avg_resting_hr' in hr:
            stories.append({
                "type": "highlight",
                "title": "Resting Heart Rate",
                "emoji": "❤️",
                "main_stat": f"{hr['avg_resting_hr']:.0f} bpm",
                "secondary": f"Lowest: {hr['lowest_resting_hr']} | Highest: {hr['highest_resting_hr']}"
            })
    
    # Story 10: Stress
    if wrapped.get("stress"):
        stress = wrapped["stress"]
        if 'avg_stress_level' in stress:
            stories.append({
                "type": "highlight",
                "title": "Stress Level",
                "emoji": "🧘",
                "main_stat": f"{stress['avg_stress_level']:.0f}/100",
                "secondary": f"Lowest: {stress['lowest_stress_day']} | Highest: {stress['highest_stress_day']}"
            })
    
    # Story 11: Steps
    if wrapped.get("steps"):
        steps = wrapped["steps"]
        if 'total_steps' in steps:
            stories.append({
                "type": "stats",
                "title": "Steps",
                "emoji": "👟",
                "stats": [
                    {"label": "Total Steps", "value": f"{steps['total_steps']:,}"},
                    {"label": "Daily Avg", "value": f"{steps['avg_daily_steps']:,.0f}"},
                    {"label": "Best Day", "value": f"{steps['most_steps_day']:,}"},
                    {"label": "10k+ Days", "value": steps['days_over_10k']}
                ]
            })
    
    # Story 12: VO2 Max
    if wrapped.get("vo2_max") and wrapped["vo2_max"]:
        vo2 = wrapped["vo2_max"]
        if 'latest_vo2_max' in vo2:
            improvement_text = ""
            if 'vo2_improvement' in vo2:
                improvement = vo2['vo2_improvement']
                symbol = "📈" if improvement > 0 else "📉"
                improvement_text = f"{symbol} {improvement:+.1f} ml/kg/min"
            
            stories.append({
                "type": "highlight",
                "title": "VO2 Max",
                "emoji": "💪",
                "main_stat": f"{vo2['latest_vo2_max']} ml/kg/min",
                "secondary": improvement_text if improvement_text else f"Highest: {vo2['highest_vo2_max']}"
            })
    
    # Story 14: Personal Records
    if wrapped.get("activities") and wrapped["activities"].get("personal_records"):
        records = wrapped["activities"]["personal_records"]
        pr_stats = []
        
        distance_names = {
            "5k": "5K",
            "10k": "10K",
            "half_marathon": "Half Marathon",
            "marathon": "Marathon"
        }
        
        for distance, record in records.items():
            if record:
                time_seconds = record.get('time_minutes', 0) * 60
                hours = int(time_seconds // 3600)
                minutes = int((time_seconds % 3600) // 60)
                secs = int(time_seconds % 60)
                
                if hours > 0:
                    time_formatted = f"{hours}:{minutes:02d}:{secs:02d}"
                else:
                    time_formatted = f"{minutes}:{secs:02d}"
                
                pr_stats.append({
                    "label": distance_names.get(distance, distance.upper()),
                    "value": time_formatted,
                    "subvalue": record.get('pace_formatted', '')
                })
        
        if pr_stats:
            stories.append({
                "type": "records",
                "title": "Personal Records",
                "emoji": "🏆",
                "records": pr_stats
            })
    
    # Story 15: Cycling Stats (if selected)
    print(f"DEBUG Story 15: Checking cycling story - 'cycling' in activity_types: {'cycling' in activity_types}")
    print(f"DEBUG Story 15: cycling data exists: {wrapped.get('activities_by_type', {}).get('cycling') is not None}")
    if 'cycling' in activity_types and wrapped.get('activities_by_type', {}).get('cycling'):
        cycling = wrapped['activities_by_type']['cycling']
        cycling_distance = convert_distance(cycling.get('total_distance_km', 0))
        print(f"DEBUG Story 15: Adding cycling story with {cycling.get('total_runs', 0)} rides")
        
        stories.append({
            "type": "running_summary",
            "title": "Cycling",
            "emoji": "⚫⚫",
            "stats": [
                {"label": "Total Rides", "value": cycling.get('total_runs', 0)},
                {"label": "Distance", "value": f"{cycling_distance:.2f} {unit_label}"},
                {"label": "Time", "value": f"{cycling.get('total_time_hours', 0):.2f} hours"},
                {"label": "Calories", "value": f"{cycling.get('total_calories', 0):,}"}
            ]
        })
        
        # Longest ride
        if cycling.get('longest_run'):
            longest_ride = cycling['longest_run']
            longest_ride_distance = convert_distance(longest_ride['distance_km'])
            stories.append({
                "type": "highlight",
                "title": "Longest Ride",
                "emoji": "⚫⚫",
                "main_stat": f"{longest_ride_distance:.2f} {unit_label}",
                "date": longest_ride.get('date', '').split('T')[0] if longest_ride.get('date') else '',
                "secondary": f"{longest_ride['duration_minutes']:.0f} minutes"
            })
    
    # Story 16: Swimming Stats (if selected)
    if 'swimming' in activity_types and wrapped.get('activities_by_type', {}).get('swimming'):
        swimming = wrapped['activities_by_type']['swimming']
        swimming_distance = convert_distance(swimming.get('total_distance_km', 0))
        
        stories.append({
            "type": "running_summary",
            "title": "Swimming",
            "emoji": "🏊",
            "stats": [
                {"label": "Total Swims", "value": swimming.get('total_runs', 0)},
                {"label": "Distance", "value": f"{swimming_distance:.2f} {unit_label}"},
                {"label": "Time", "value": f"{swimming.get('total_time_hours', 0):.2f} hours"},
                {"label": "Calories", "value": f"{swimming.get('total_calories', 0):,}"}
            ]
        })
        
        # Longest swim
        if swimming.get('longest_run'):
            longest_swim = swimming['longest_run']
            longest_swim_distance = convert_distance(longest_swim['distance_km'])
            stories.append({
                "type": "highlight",
                "title": "Longest Swim",
                "emoji": "🏊",
                "main_stat": f"{longest_swim_distance:.2f} {unit_label}",
                "date": longest_swim.get('date', '').split('T')[0] if longest_swim.get('date') else '',
                "secondary": f"{longest_swim['duration_minutes']:.0f} minutes"
            })
    
    # Story 17: Others Stats (if selected)
    if 'others' in activity_types and wrapped.get('activities_by_type', {}).get('others'):
        others = wrapped['activities_by_type']['others']
        others_distance = convert_distance(others.get('total_distance_km', 0))
        most_common = others.get('most_common_activity_type', 'Unknown')
        
        # Format activity type name (e.g., "hiking" -> "Hiking")
        most_common_formatted = most_common.replace('_', ' ').title()
        
        stories.append({
            "type": "running_summary",
            "title": "Other Activities",
            "emoji": "⋯",
            "stats": [
                {"label": "Total Activities", "value": others.get('total_runs', 0)},
                {"label": "Most Common", "value": most_common_formatted},
                {"label": "Time", "value": f"{others.get('total_time_hours', 0):.2f} hours"},
                {"label": "Calories", "value": f"{others.get('total_calories', 0):,}"}
            ]
        })
        
        # Longest other activity (by time, not distance)
        if others.get('longest_by_time'):
            longest_other = others['longest_by_time']
            activity_type = longest_other.get('activity_type', 'Unknown')
            activity_type_formatted = activity_type.replace('_', ' ').title()
            
            stories.append({
                "type": "highlight",
                "title": "Longest Activity",
                "emoji": "⋯",
                "main_stat": f"{longest_other['duration_minutes']:.0f} min",
                "date": longest_other.get('date', '').split('T')[0] if longest_other.get('date') else '',
                "secondary": activity_type_formatted
            })
    
    # AI Insights (cached)
    # Check if we have cached insights for this user
    cached_insights = None
    if email:
        cached_insights = load_insights(email)
    
    if cached_insights:
        ai_insights = cached_insights.get('insights', '')
        ai_forecast = cached_insights.get('forecast', '')
    else:
        # Generate new insights and cache them
        ai_insights = generate_ai_insights(wrapped)
        ai_forecast = generate_ai_forecast(wrapped, ai_insights)
        if email:
            save_insights(email, ai_insights, ai_forecast)
    
    stories.append({
        "type": "ai_text",
        "title": "Your Year Insights",
        "emoji": "target",
        "text": ai_insights
    })
    
    # AI Forecast for Next Year
    stories.append({
        "type": "ai_text",
        "title": "2026 Goals",
        "emoji": "arrow-right",
        "text": ai_forecast
    })
    
    # Final Story: Summary
    activities = wrapped.get("activities", {})
    sleep = wrapped.get("sleep", {})
    
    # Build summary based on activity types
    summary_items = []
    
    # Add running stats
    if activities.get('total_distance_km', 0) > 0:
        run_distance = convert_distance(activities.get('total_distance_km', 0))
        summary_items.append(f"{run_distance:.0f} {unit_label} run")
        summary_items.append(f"{activities.get('total_runs', 0)} runs completed")
    
    # Add cycling stats if selected
    if 'cycling' in activity_types and wrapped.get('activities_by_type', {}).get('cycling'):
        cycling = wrapped['activities_by_type']['cycling']
        cycling_distance = convert_distance(cycling.get('total_distance_km', 0))
        if cycling_distance > 0:
            summary_items.append(f"{cycling_distance:.0f} {unit_label} cycled")
    
    # Add swimming stats if selected
    if 'swimming' in activity_types and wrapped.get('activities_by_type', {}).get('swimming'):
        swimming = wrapped['activities_by_type']['swimming']
        swimming_distance = convert_distance(swimming.get('total_distance_km', 0))
        if swimming_distance > 0:
            summary_items.append(f"{swimming_distance:.0f} {unit_label} swam")
    
    # Add sleep
    if sleep.get('total_sleep_hours', 0) > 0:
        summary_items.append(f"{sleep.get('total_sleep_hours', 0):.0f} hours slept")
    
    stories.append({
        "type": "summary",
        "title": "That's a Wrap!",
        "emoji": "🎊",
        "summary": summary_items[:5]  # Limit to 5 items to avoid overcrowding
    })
    
    return stories

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    app.run(debug=True, port=5000)