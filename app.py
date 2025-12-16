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

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Handle logout request."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200

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
    
    if not email or not password:
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': 'Not logged in'})}\n\n",
            mimetype='text/event-stream'
        )
    
    def generate():
        global wrapped_data
        
        # Capture email from outer scope
        user_email = email
        
        # Create a queue to communicate between threads
        message_queue = queue.Queue()
        
        def progress_callback(message):
            # Put message in queue
            message_queue.put(message)
        
        def run_wrapped_generation():
            try:
                # Use credentials passed from main thread
                
                # Try to load cached data first
                print("Thread: Checking for cached data...")
                cached_data = load_wrapped_data(email)
                
                if cached_data:
                    print("Thread: Using cached data")
                    progress_callback("Loading your saved Wrapped data...")
                    message_queue.put(('COMPLETE', cached_data))
                    return
                
                print("Thread: No cache found, starting Garmin initialization...")
                # Initialize Garmin
                garmin = GarminWrapped(
                    email=email,
                    password=password
                )
                
                print("Thread: Calling generate_wrapped_2025...")
                # Generate with progress callback
                global wrapped_data
                wrapped_data = garmin.generate_wrapped_2025(progress_callback=progress_callback)
                
                # Save the generated data
                print("Thread: Saving wrapped data to file...")
                save_wrapped_data(email, wrapped_data)
                
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
            
            # Format data for stories
            stories = format_stories(wrapped_data, user_email)
            
            # Send completion with data
            yield f"data: {json.dumps({'type': 'complete', 'stories': stories})}\n\n"
            
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
    stories = format_stories(wrapped_data, email)
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

def format_stories(wrapped, email=None):
    """Format wrapped data into story slides."""
    stories = []
    
    # Story 1: Welcome
    stories.append({
        "type": "welcome",
        "title": "Your 2025",
        "subtitle": "Garmin Wrapped",
        "emoji": "🎉"
    })
    
    # Story 2: Running Summary
    if wrapped.get("activities"):
        activities = wrapped["activities"]
        stories.append({
            "type": "running_summary",
            "title": "Running",
            "emoji": "🏃",
            "stats": [
                {"label": "Total Runs", "value": activities.get('total_runs', 0)},
                {"label": "Distance", "value": f"{activities.get('total_distance_km', 0):.2f} km"},
                {"label": "Time", "value": f"{activities.get('total_time_hours', 0):.2f} hours"},
                {"label": "Calories", "value": f"{activities.get('total_calories', 0):,}"}
            ]
        })
        
        # Story 3: Longest Run
        if activities.get('longest_run'):
            longest = activities['longest_run']
            stories.append({
                "type": "highlight",
                "title": "Longest Run",
                "emoji": "🏆",
                "main_stat": f"{longest['distance_km']:.2f} km",
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
                    months_data.append({
                        "name": month_names[i-1],
                        "distance": f"{stat['total_distance_km']:.0f}",
                        "runs": stat['count'],
                        "pace": stat.get('avg_pace_formatted', '0:00'),
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
                    "months": months_data
                })
        
        # Story 5: Fastest Pace
        if activities.get('fastest_pace'):
            fastest = activities['fastest_pace']
            stories.append({
                "type": "highlight",
                "title": "Fastest Pace",
                "emoji": "⚡",
                "main_stat": fastest.get('pace_formatted', '0:00') + "/km",
                "date": fastest.get('date', '').split('T')[0] if fastest.get('date') else '',
                "secondary": f"{fastest['distance_km']:.2f} km run"
            })
        
        # Story 6: Averages
        if activities.get('averages'):
            avg = activities['averages']
            stories.append({
                "type": "stats",
                "title": "Your Averages",
                "emoji": "📊",
                "stats": [
                    {"label": "Distance", "value": f"{avg['distance_km']:.2f} km"},
                    {"label": "Pace", "value": avg.get('pace_formatted', '0:00') + "/km"},
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
    
    # Story 15: AI Insights (cached)
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
    
    # Story 16: AI Forecast for Next Year
    stories.append({
        "type": "ai_text",
        "title": "2026 Goals",
        "emoji": "arrow-right",
        "text": ai_forecast
    })
    
    # Story 17: Final Summary
    activities = wrapped.get("activities", {})
    sleep = wrapped.get("sleep", {})
    stories.append({
        "type": "summary",
        "title": "That's a Wrap!",
        "emoji": "🎊",
        "summary": [
            f"{activities.get('total_distance_km', 0):.0f} km run",
            f"{sleep.get('total_sleep_hours', 0):.0f} hours slept",
            f"{activities.get('total_runs', 0)} runs completed"
        ]
    })
    
    return stories

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    app.run(debug=True, port=5000)