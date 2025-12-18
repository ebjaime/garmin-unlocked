from garminconnect import Garmin
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

class GarminWrapped:
    """
    Backend for generating Spotify Wrapped-style insights from Garmin data.
    Uses the garminconnect library to fetch activities and health metrics.
    """
    
    def __init__(self, email: str, password: str):
        """
        Initialize with Garmin Connect credentials.
        
        Args:
            email: Garmin Connect email
            password: Garmin Connect password
        """
        self.email = email
        self.password = password
        self.client = None
    
    @staticmethod
    def format_pace(pace_decimal: float) -> str:
        """
        Convert pace from decimal minutes to MM:SS format.
        
        Args:
            pace_decimal: Pace in decimal minutes (e.g., 5.5 = 5:30)
            
        Returns:
            Formatted pace string (e.g., "5:30")
        """
        if not pace_decimal or pace_decimal <= 0:
            return "0:00"
        
        minutes = int(pace_decimal)
        seconds = int((pace_decimal - minutes) * 60)
        return f"{minutes}:{seconds:02d}"
        
    def authenticate(self) -> bool:
        """Authenticate with Garmin Connect."""
        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            print("✓ Authentication successful!")
            return True
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            return False
    
    def get_activities(self, start_date: str, end_date: str, activity_type: str = "running") -> List[Dict]:
        """
        Fetch activities from Garmin Connect.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            activity_type: Type of activity (default: running, or 'others' for everything else)
            
        Returns:
            List of activity dictionaries
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            # Get activities
            activities = self.client.get_activities_by_date(start_date, end_date)
            
            # Filter by activity type
            filtered_activities = []
            
            if activity_type.lower() == 'others':
                # For 'others', include everything that's NOT running, cycling, or swimming
                for activity in activities:
                    activity_type_name = activity.get('activityType', {}).get('typeKey', '').lower()
                    is_running = 'running' in activity_type_name or 'run' in activity_type_name
                    is_cycling = 'cycling' in activity_type_name or 'biking' in activity_type_name or 'bike' in activity_type_name
                    is_swimming = 'swimming' in activity_type_name or 'swim' in activity_type_name
                    
                    if not is_running and not is_cycling and not is_swimming:
                        filtered_activities.append(activity)
            else:
                # Normal filtering - match activity type with improved specificity
                for activity in activities:
                    activity_type_name = activity.get('activityType', {}).get('typeKey', '').lower()
                    
                    # Special handling for cycling to be more specific
                    if activity_type.lower() == 'cycling':
                        is_cycling = ('cycling' in activity_type_name or 
                                     'biking' in activity_type_name or 
                                     'bike' in activity_type_name or
                                     'mountain_biking' in activity_type_name or
                                     'road_biking' in activity_type_name or
                                     'gravel_cycling' in activity_type_name)
                        if is_cycling:
                            filtered_activities.append(activity)
                    # Special handling for swimming
                    elif activity_type.lower() == 'swimming':
                        is_swimming = ('swimming' in activity_type_name or 
                                      'swim' in activity_type_name or
                                      'lap_swimming' in activity_type_name or
                                      'open_water_swimming' in activity_type_name)
                        if is_swimming:
                            filtered_activities.append(activity)
                    # Default matching for other types like running
                    elif activity_type.lower() in activity_type_name:
                        filtered_activities.append(activity)
            
            print(f"✓ Found {len(filtered_activities)} {activity_type} activities")
            if len(filtered_activities) > 0:
                print(f"  Sample activity types found: {[a.get('activityType', {}).get('typeKey', '') for a in filtered_activities[:3]]}")
            return filtered_activities
            
        except Exception as e:
            print(f"✗ Error fetching activities: {e}")
            return []
    
    def get_sleep_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch sleep data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of sleep data dictionaries
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            sleep_data = []
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                try:
                    sleep = self.client.get_sleep_data(date_str)
                    if sleep:
                        sleep_data.append(sleep)
                except:
                    pass
                current += timedelta(days=1)
            
            print(f"✓ Found {len(sleep_data)} sleep records")
            return sleep_data
            
        except Exception as e:
            print(f"✗ Error fetching sleep data: {e}")
            return []
    
    def get_stress_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch stress data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of stress data points
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            stress_data = []
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                try:
                    stress = self.client.get_stress_data(date_str)
                    if stress:
                        stress_data.append(stress)
                except:
                    pass
                current += timedelta(days=1)
            
            print(f"✓ Found {len(stress_data)} stress records")
            return stress_data
            
        except Exception as e:
            print(f"✗ Error fetching stress data: {e}")
            return []
    
    def get_heart_rate_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch heart rate data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of heart rate data
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            hr_data = []
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                try:
                    hr = self.client.get_heart_rates(date_str)
                    if hr:
                        hr_data.append(hr)
                except:
                    pass
                current += timedelta(days=1)
            
            print(f"✓ Found {len(hr_data)} heart rate records")
            return hr_data
            
        except Exception as e:
            print(f"✗ Error fetching heart rate data: {e}")
            return []
    
    def get_body_battery_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch Body Battery data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of Body Battery data
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            bb_data = []
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                try:
                    bb = self.client.get_body_battery(date_str)
                    if bb:
                        bb_data.append(bb)
                except:
                    pass
                current += timedelta(days=1)
            
            print(f"✓ Found {len(bb_data)} Body Battery records")
            return bb_data
            
        except Exception as e:
            print(f"✗ Error fetching Body Battery data: {e}")
            return []
    
    def get_steps_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch daily steps data.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of steps data
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            steps_data = []
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                try:
                    steps = self.client.get_steps_data(date_str)
                    if steps:
                        steps_data.append(steps)
                except:
                    pass
                current += timedelta(days=1)
            
            print(f"✓ Found {len(steps_data)} steps records")
            return steps_data
            
        except Exception as e:
            print(f"✗ Error fetching steps data: {e}")
            return []
    
    def get_vo2_max_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch VO2 Max data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of VO2 Max data
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            vo2_data = []
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                try:
                    max_metrics = self.client.get_max_metrics(date_str)
                    if max_metrics and isinstance(max_metrics, list) and len(max_metrics) > 0:
                        generic = max_metrics[0].get('generic', {})
                        vo2_value = generic.get('vo2MaxPreciseValue') or generic.get('vo2MaxValue')
                        if vo2_value:
                            vo2_data.append({
                                'date': date_str,
                                'vo2Max': vo2_value
                            })
                except:
                    pass
                current += timedelta(days=1)
            
            print(f"✓ Found {len(vo2_data)} VO2 Max records")
            return vo2_data
            
        except Exception as e:
            print(f"✗ Error fetching VO2 Max data: {e}")
            return []
    
    def get_training_status_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch training status/load data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of training status data
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            training_data = []
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                try:
                    status = self.client.get_training_status(date_str)
                    if status:
                        training_data.append({
                            'date': date_str,
                            'raw_data': status
                        })
                except:
                    pass
                current += timedelta(days=1)
            
            print(f"✓ Found {len(training_data)} training status records")
            return training_data
            
        except Exception as e:
            print(f"✗ Error fetching training status data: {e}")
            return []
    
    def get_all_time_personal_records(self) -> Dict:
        """
        Fetch all-time personal records from Garmin.
        
        Returns:
            Dictionary of all-time personal records
        """
        if not self.client:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            prs = self.client.get_personal_record()
            print(f"✓ Retrieved all-time personal records")
            return prs
        except Exception as e:
            print(f"✗ Error fetching personal records: {e}")
            return {}
    
    def calculate_sleep_insights(self, sleep_data: List[Dict]) -> Dict:
        """Calculate sleep-related insights."""
        if not sleep_data:
            return {}
        
        sleep_scores = []
        sleep_durations = []
        deep_sleep = []
        light_sleep = []
        rem_sleep = []
        awake_time = []
        
        for day in sleep_data:
            sleep_dto = day.get('dailySleepDTO', day)  # Handle both structures
            
            # Sleep score
            score = sleep_dto.get('overallSleepScore', {}).get('value') if isinstance(sleep_dto.get('overallSleepScore'), dict) else sleep_dto.get('overallSleepScore')
            if score:
                sleep_scores.append(score)
            
            # Duration (in seconds, convert to hours)
            duration = sleep_dto.get('sleepTimeSeconds')
            if duration:
                sleep_durations.append(duration / 3600)
            
            # Sleep stages
            deep = sleep_dto.get('deepSleepSeconds')
            if deep:
                deep_sleep.append(deep / 3600)
            
            light = sleep_dto.get('lightSleepSeconds')
            if light:
                light_sleep.append(light / 3600)
            
            rem = sleep_dto.get('remSleepSeconds')
            if rem:
                rem_sleep.append(rem / 3600)
            
            awake = sleep_dto.get('awakeSleepSeconds')
            if awake:
                awake_time.append(awake / 60)  # in minutes
        
        insights = {}
        
        if sleep_scores:
            insights['avg_sleep_score'] = round(statistics.mean(sleep_scores), 1)
            insights['best_sleep_score'] = max(sleep_scores)
            insights['worst_sleep_score'] = min(sleep_scores)
        
        if sleep_durations:
            insights['avg_sleep_hours'] = round(statistics.mean(sleep_durations), 1)
            insights['total_sleep_hours'] = round(sum(sleep_durations), 1)
            insights['longest_sleep_hours'] = round(max(sleep_durations), 1)
        
        if deep_sleep:
            insights['avg_deep_sleep_hours'] = round(statistics.mean(deep_sleep), 1)
        
        if light_sleep:
            insights['avg_light_sleep_hours'] = round(statistics.mean(light_sleep), 1)
        
        if rem_sleep:
            insights['avg_rem_sleep_hours'] = round(statistics.mean(rem_sleep), 1)
        
        if awake_time:
            insights['avg_awake_minutes'] = round(statistics.mean(awake_time), 1)
        
        return insights
    
    def calculate_stress_insights(self, stress_data: List[Dict]) -> Dict:
        """Calculate stress-related insights."""
        if not stress_data:
            return {}
        
        avg_stress = []
        max_stress = []
        
        for day in stress_data:
            avg = day.get('avgStressLevel')
            if avg and avg > 0:
                avg_stress.append(avg)
            
            max_val = day.get('maxStressLevel')
            if max_val and max_val > 0:
                max_stress.append(max_val)
        
        insights = {}
        
        if avg_stress:
            insights['avg_stress_level'] = round(statistics.mean(avg_stress), 1)
            insights['highest_stress_day'] = max(avg_stress)
            insights['lowest_stress_day'] = min(avg_stress)
        
        return insights
    
    def calculate_hr_insights(self, hr_data: List[Dict]) -> Dict:
        """Calculate heart rate insights."""
        if not hr_data:
            return {}
        
        resting_hr = []
        max_hr = []
        
        for day in hr_data:
            resting = day.get('restingHeartRate')
            if resting and resting > 0:
                resting_hr.append(resting)
            
            max_val = day.get('maxHeartRate')
            if max_val and max_val > 0:
                max_hr.append(max_val)
        
        insights = {}
        
        if resting_hr:
            insights['avg_resting_hr'] = round(statistics.mean(resting_hr), 1)
            insights['lowest_resting_hr'] = min(resting_hr)
            insights['highest_resting_hr'] = max(resting_hr)
        
        if max_hr:
            insights['avg_max_hr'] = round(statistics.mean(max_hr), 1)
        
        return insights
    
    def calculate_body_battery_insights(self, bb_data: List[Dict]) -> Dict:
        """Calculate Body Battery insights."""
        if not bb_data:
            return {}
        
        charged = []
        drained = []
        
        for day in bb_data:
            charged_val = day[0].get('charged')
            if charged_val:
                charged.append(charged_val)
            
            drained_val = day[0].get('drained')
            if drained_val:
                drained.append(abs(drained_val))
        
        insights = {}
        
        if charged:
            insights['avg_battery_charged'] = round(statistics.mean(charged), 1)
            insights['best_recharge_day'] = max(charged)
        
        if drained:
            insights['avg_battery_drained'] = round(statistics.mean(drained), 1)
            insights['most_draining_day'] = max(drained)
        
        return insights
    
    def calculate_steps_insights(self, steps_data: List[Dict]) -> Dict:
        """Calculate steps insights."""
        if not steps_data:
            return {}
        
        daily_steps = []
        
        for day in steps_data:
            # Steps data is an array of 15-minute intervals
            if isinstance(day, list):
                day_total = sum(interval.get('steps', 0) for interval in day)
                if day_total > 0:
                    daily_steps.append(day_total)
            elif isinstance(day, dict):
                # Handle if it's a single dict with totalSteps
                steps = day.get('totalSteps')
                if steps and steps > 0:
                    daily_steps.append(steps)
        
        insights = {}
        
        if daily_steps:
            insights['total_steps'] = sum(daily_steps)
            insights['avg_daily_steps'] = round(statistics.mean(daily_steps), 0)
            insights['most_steps_day'] = max(daily_steps)
            insights['days_over_10k'] = sum(1 for s in daily_steps if s >= 10000)
        
        return insights
    
    def calculate_vo2_max_insights(self, vo2_data: List[Dict]) -> Dict:
        """Calculate VO2 Max insights."""
        if not vo2_data:
            return {}
        
        vo2_values = [d['vo2Max'] for d in vo2_data if d.get('vo2Max')]
        
        insights = {}
        
        if vo2_values:
            insights['latest_vo2_max'] = vo2_values[-1]
            insights['highest_vo2_max'] = max(vo2_values)
            insights['lowest_vo2_max'] = min(vo2_values)
            insights['avg_vo2_max'] = round(statistics.mean(vo2_values), 1)
            
            # Calculate improvement
            if len(vo2_values) > 1:
                first_vo2 = vo2_values[0]
                last_vo2 = vo2_values[-1]
                improvement = last_vo2 - first_vo2
                insights['vo2_improvement'] = round(improvement, 1)
                insights['vo2_improvement_percent'] = round((improvement / first_vo2) * 100, 1)
        
        return insights
    
    def calculate_training_load_insights(self, training_data: List[Dict]) -> Dict:
        """Calculate Training Load insights."""
        if not training_data:
            return {}
        
        loads_acute = []
        loads_chronic = []
        statuses = []
        status_phrases = []
        
        for day in training_data:
            raw_data = day.get('raw_data', {})
            
            # Extract training status
            most_recent = raw_data.get('mostRecentTrainingStatus') or {}
            latest_data = most_recent.get('latestTrainingStatusData') or {}
            
            for device_id, device_data in latest_data.items():
                # Acute training load
                acute_dto = device_data.get('acuteTrainingLoadDTO', {})
                acute_load = acute_dto.get('dailyTrainingLoadAcute')
                if acute_load and acute_load > 0:
                    loads_acute.append(acute_load)
                
                chronic_load = acute_dto.get('dailyTrainingLoadChronic')
                if chronic_load and chronic_load > 0:
                    loads_chronic.append(chronic_load)
                
                # Training status
                status = device_data.get('trainingStatus')
                if status:
                    statuses.append(status)
                
                status_phrase = device_data.get('trainingStatusFeedbackPhrase')
                if status_phrase:
                    status_phrases.append(status_phrase)
        
        insights = {}
        
        if loads_acute:
            insights['avg_acute_training_load'] = round(statistics.mean(loads_acute), 1)
            insights['highest_acute_load'] = round(max(loads_acute), 1)
            insights['latest_acute_load'] = round(loads_acute[-1], 1)
        
        if loads_chronic:
            insights['avg_chronic_training_load'] = round(statistics.mean(loads_chronic), 1)
            insights['latest_chronic_load'] = round(loads_chronic[-1], 1)
        
        if status_phrases:
            status_counts = {}
            for phrase in status_phrases:
                status_counts[phrase] = status_counts.get(phrase, 0) + 1
            insights['training_status_distribution'] = status_counts
            insights['most_common_status'] = max(status_counts, key=status_counts.get)
        
        return insights
    
    def calculate_activity_insights(self, activities: List[Dict]) -> Dict:
        """Calculate activity insights."""
        if not activities:
            return {}
        
        distances = []
        durations = []
        paces = []
        elevations = []
        dates = []
        calories = []
        avg_hrs = []
        countries = set()  # Track unique countries
        activity_types = []  # Track activity types for "others"
        activities_with_data = []  # Store activities with their processed data
        
        for activity in activities:
            distance = activity.get('distance', 0)
            duration = activity.get('duration', 0)
            elevation = activity.get('elevationGain', 0)
            date = activity.get('startTimeLocal', '')
            calorie = activity.get('calories', 0)
            avg_hr = activity.get('averageHR', 0)
            activity_type = activity.get('activityType', {}).get('typeKey', 'Unknown')
            
            # Track activity types
            activity_types.append(activity_type)
            
            # Extract country from location name if available
            location_name = activity.get('locationName', '')
            if location_name:
                # Location names often come in format "City, Country" or just "Country"
                parts = location_name.split(',')
                if len(parts) > 0:
                    country = parts[-1].strip()  # Get the last part as country
                    if country:
                        countries.add(country)
            
            if distance > 0 and duration > 0:
                distances.append(distance)
                durations.append(duration)
                elevations.append(elevation)
                dates.append(date)
                calories.append(calorie)
                if avg_hr > 0:
                    avg_hrs.append(avg_hr)
                
                pace = (duration / 60) / (distance / 1000)
                paces.append(pace)
                
                # Store activity with its data for finding longest by time
                activities_with_data.append({
                    'distance': distance,
                    'duration': duration,
                    'date': date,
                    'type': activity_type
                })
        
        insights = {
            "total_runs": len(activities),
            "total_distance_km": round(sum(distances) / 1000, 2),
            "total_time_hours": round(sum(durations) / 3600, 2),
            "total_elevation_m": round(sum(elevations), 0),
            "total_calories": sum(calories),
            
            "longest_run": {
                "distance_km": round(max(distances) / 1000, 2) if distances else 0,
                "date": dates[distances.index(max(distances))] if distances else None,
                "duration_minutes": round(durations[distances.index(max(distances))] / 60, 2) if distances else 0
            },
            
            "longest_by_time": {
                "duration_minutes": round(max(durations) / 60, 2) if durations else 0,
                "date": dates[durations.index(max(durations))] if durations else None,
                "distance_km": round(distances[durations.index(max(durations))] / 1000, 2) if durations else 0,
                "activity_type": activities_with_data[durations.index(max(durations))]['type'] if activities_with_data and durations else 'Unknown'
            },
            
            "most_common_activity_type": max(set(activity_types), key=activity_types.count) if activity_types else 'Unknown',
            
            "fastest_pace": {
                "pace_min_km": round(min(paces), 2) if paces else 0,
                "pace_formatted": self.format_pace(min(paces)) if paces else "0:00",
                "date": dates[paces.index(min(paces))] if paces else None,
                "distance_km": round(distances[paces.index(min(paces))] / 1000, 2) if paces else 0
            },
            
            "most_elevation": {
                "elevation_m": round(max(elevations), 0) if elevations else 0,
                "date": dates[elevations.index(max(elevations))] if elevations else None,
                "distance_km": round(distances[elevations.index(max(elevations))] / 1000, 2) if elevations else 0
            },
            
            "averages": {
                "distance_km": round(statistics.mean(distances) / 1000, 2) if distances else 0,
                "pace_min_km": round(statistics.mean(paces), 2) if paces else 0,
                "pace_formatted": self.format_pace(statistics.mean(paces)) if paces else "0:00",
                "duration_minutes": round(statistics.mean(durations) / 60, 2) if durations else 0,
                "heart_rate_bpm": round(statistics.mean(avg_hrs), 0) if avg_hrs else 0,
                "calories_per_run": round(statistics.mean(calories), 0) if calories else 0
            },
            
            "frequency": {
                "runs_per_week": round(self._calculate_frequency(dates), 2),
                "runs_per_month": round(len(activities) / 12, 2) if len(activities) > 0 else 0
            },
            
            "countries": {
                "unique_countries": sorted(list(countries)),
                "total_countries": len(countries)
            },
            
            "personal_records": self._identify_records(activities),
            "monthly_stats": self._calculate_monthly_stats(activities)
        }
        
        return insights
    
    def _calculate_frequency(self, dates: List[str]) -> float:
        """Calculate average runs per week."""
        if not dates or len(dates) < 2:
            return 0
        
        try:
            parsed_dates = []
            for d in dates:
                try:
                    if 'T' in d:
                        parsed_dates.append(datetime.fromisoformat(d.replace('Z', '+00:00')))
                    else:
                        parsed_dates.append(datetime.strptime(d, "%Y-%m-%d"))
                except:
                    continue
            
            if len(parsed_dates) < 2:
                return 0
            
            parsed_dates.sort()
            first_date = parsed_dates[0]
            last_date = parsed_dates[-1]
            weeks = (last_date - first_date).days / 7
            
            if weeks == 0:
                return len(dates)
            
            return len(dates) / weeks
        except:
            return 0
    
    def _identify_records(self, activities: List[Dict]) -> Dict:
        """Identify personal records for standard race distances."""
        records = {
            "5k": None,
            "10k": None,
            "half_marathon": None,
            "marathon": None
        }
        
        for activity in activities:
            distance = activity.get('distance', 0) / 1000
            duration = activity.get('duration', 0) / 60
            date = activity.get('startTimeLocal', '')
            
            if 4.8 <= distance <= 5.2:
                if records["5k"] is None or duration < records["5k"]["time_minutes"]:
                    pace = duration / distance
                    records["5k"] = {
                        "time_minutes": round(duration, 2),
                        "pace_min_km": round(pace, 2),
                        "pace_formatted": self.format_pace(pace),
                        "date": date
                    }
            
            if 9.8 <= distance <= 10.2:
                if records["10k"] is None or duration < records["10k"]["time_minutes"]:
                    pace = duration / distance
                    records["10k"] = {
                        "time_minutes": round(duration, 2),
                        "pace_min_km": round(pace, 2),
                        "pace_formatted": self.format_pace(pace),
                        "date": date
                    }
            
            if 20.5 <= distance <= 21.5:
                if records["half_marathon"] is None or duration < records["half_marathon"]["time_minutes"]:
                    pace = duration / distance
                    records["half_marathon"] = {
                        "time_minutes": round(duration, 2),
                        "pace_min_km": round(pace, 2),
                        "pace_formatted": self.format_pace(pace),
                        "date": date
                    }
            
            if 42.0 <= distance <= 43.0:
                if records["marathon"] is None or duration < records["marathon"]["time_minutes"]:
                    pace = duration / distance
                    records["marathon"] = {
                        "time_minutes": round(duration, 2),
                        "pace_min_km": round(pace, 2),
                        "pace_formatted": self.format_pace(pace),
                        "date": date
                    }
        
        return records
    
    def _calculate_monthly_stats(self, activities: List[Dict]) -> Dict:
        """Calculate statistics by month."""
        monthly = {}
        errors = 0
        
        for activity in activities:
            date_str = activity.get('startTimeLocal', '')
            if not date_str:
                continue
            
            try:
                # Handle various date formats from Garmin API
                if 'T' in date_str:
                    # ISO format: 2025-11-30T08:35:00 or 2025-11-30T08:35:00Z
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                elif ' ' in date_str:
                    # Space-separated format: 2025-11-30 08:35:00
                    date = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                else:
                    # Date only: 2025-11-30
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                
                month_key = date.strftime("%Y-%m")
                
                if month_key not in monthly:
                    monthly[month_key] = {
                        "count": 0,
                        "total_distance_km": 0,
                        "total_time_hours": 0,
                        "total_duration_seconds": 0
                    }
                
                monthly[month_key]["count"] += 1
                monthly[month_key]["total_distance_km"] += activity.get('distance', 0) / 1000
                monthly[month_key]["total_time_hours"] += activity.get('duration', 0) / 3600
                monthly[month_key]["total_duration_seconds"] += activity.get('duration', 0)
            except Exception as e:
                errors += 1
                continue
        
        if errors > 0:
            print(f"⚠️  Skipped {errors} activities due to date parsing errors")
        
        for month in monthly:
            monthly[month]["total_distance_km"] = round(monthly[month]["total_distance_km"], 2)
            monthly[month]["total_time_hours"] = round(monthly[month]["total_time_hours"], 2)
            
            # Calculate average pace (min/km)
            if monthly[month]["total_distance_km"] > 0 and monthly[month]["total_duration_seconds"] > 0:
                pace_min_km = (monthly[month]["total_duration_seconds"] / 60) / monthly[month]["total_distance_km"]
                monthly[month]["avg_pace_min_km"] = round(pace_min_km, 2)
                monthly[month]["avg_pace_formatted"] = self.format_pace(pace_min_km)
            else:
                monthly[month]["avg_pace_min_km"] = 0
                monthly[month]["avg_pace_formatted"] = "0:00"
        
        return monthly
    
    def generate_wrapped_2025(self, progress_callback=None, activity_types=None) -> Dict:
        """
        Generate comprehensive Wrapped insights for 2025.
        Uses parallel data fetching to significantly reduce load time.
        
        Args:
            progress_callback: Optional generator function to yield progress updates
            activity_types: List of activity types to fetch (default: ['running'])
        
        Returns:
            Dictionary with 2025 insights including activities, sleep, stress, and more
        """
        if activity_types is None:
            activity_types = ['running']
            
        def update_progress(message):
            print(f"🔄 {message}")
            if progress_callback:
                progress_callback(message)
        
        if not self.authenticate():
            return {"error": "Authentication failed"}
        
        update_progress("Fetching your data in parallel...")
        
        # Define all data fetching tasks
        tasks = {
            'sleep_data': lambda: self.get_sleep_data("2025-01-01", "2025-12-31"),
            'stress_data': lambda: self.get_stress_data("2025-01-01", "2025-12-31"),
            'hr_data': lambda: self.get_heart_rate_data("2025-01-01", "2025-12-31"),
            'bb_data': lambda: self.get_body_battery_data("2025-01-01", "2025-12-31"),
            'steps_data': lambda: self.get_steps_data("2025-01-01", "2025-12-31"),
            'vo2_data': lambda: self.get_vo2_max_data("2025-01-01", "2025-12-31"),
            'training_data': lambda: self.get_training_status_data("2025-01-01", "2025-12-31"),
            'all_time_prs': lambda: self.get_all_time_personal_records()
        }
        
        # Add activity fetching tasks for each selected type
        for activity_type in activity_types:
            tasks[f'activities_{activity_type}'] = lambda at=activity_type: self.get_activities("2025-01-01", "2025-12-31", at)
        
        results = {}
        completed = 0
        total = len(tasks)
        
        # Execute all tasks in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            future_to_name = {executor.submit(task): name for name, task in tasks.items()}
            
            # Collect results as they complete
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                completed += 1
                
                try:
                    results[name] = future.result()
                    update_progress(f"Loaded {name.replace('_', ' ')}... ({completed}/{total})")
                except Exception as e:
                    print(f"❌ Error fetching {name}: {e}")
                    results[name] = [] if name != 'all_time_prs' else {}
        
        # Calculate insights
        update_progress("Crunching the numbers...")
        
        # Calculate insights for each activity type separately
        activities_by_type = {}
        for activity_type in activity_types:
            activities_key = f'activities_{activity_type}'
            if activities_key in results and results[activities_key]:
                activities_by_type[activity_type] = self.calculate_activity_insights(results[activities_key])
        
        # For running, use the running-specific data, otherwise combine all
        if 'running' in activities_by_type:
            main_activities = activities_by_type['running']
        else:
            # If no running, combine all activities
            all_activities = []
            for activity_type in activity_types:
                activities_key = f'activities_{activity_type}'
                if activities_key in results:
                    all_activities.extend(results[activities_key])
            main_activities = self.calculate_activity_insights(all_activities) if all_activities else {}
        
        wrapped = {
            "activities": main_activities,  # Main story uses running or combined
            "activities_by_type": activities_by_type,  # Separate insights per activity type
            "activity_types": activity_types,  # Store which types were included
            "sleep": self.calculate_sleep_insights(results['sleep_data']),
            "stress": self.calculate_stress_insights(results['stress_data']),
            "heart_rate": self.calculate_hr_insights(results['hr_data']),
            "body_battery": self.calculate_body_battery_insights(results['bb_data']),
            "steps": self.calculate_steps_insights(results['steps_data']),
            "vo2_max": self.calculate_vo2_max_insights(results['vo2_data']),
            "training_load": self.calculate_training_load_insights(results['training_data']),
            "all_time_prs": self._parse_all_time_prs(results['all_time_prs'])
        }
        
        update_progress("Your Wrapped is ready! 🎉")
        return wrapped
    
    def _parse_all_time_prs(self, pr_data: Dict) -> Dict:
        """Parse all-time personal records from Garmin API response."""
        if not pr_data:
            return {}
        
        parsed_prs = {}
        
        # Garmin returns PRs as an array of records with typeId
        # typeId mapping: 5=5K, 6=10K, 7=Marathon, 8=Half Marathon
        if isinstance(pr_data, list):
            for record in pr_data:
                type_id = record.get('typeId')
                value = record.get('value')  # Value is in seconds for time-based PRs
                pr_date = record.get('actStartDateTimeInGMTFormatted')
                
                if not value:
                    continue
                
                # Map typeId to distance
                if type_id == 5:  # 5K
                    parsed_prs['5k'] = {
                        'time_seconds': value,
                        'time_formatted': self._format_time(value),
                        'date': pr_date
                    }
                elif type_id == 6:  # 10K
                    parsed_prs['10k'] = {
                        'time_seconds': value,
                        'time_formatted': self._format_time(value),
                        'date': pr_date
                    }
                elif type_id == 7:  # Marathon (42.195 km)
                    parsed_prs['marathon'] = {
                        'time_seconds': value,
                        'time_formatted': self._format_time(value),
                        'date': pr_date
                    }
                elif type_id == 8:  # Half Marathon (21.0975 km)
                    parsed_prs['half_marathon'] = {
                        'time_seconds': value,
                        'time_formatted': self._format_time(value),
                        'date': pr_date
                    }
        
        return parsed_prs
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        if not seconds:
            return "0:00:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def print_wrapped_summary(self, wrapped: Dict):
        """Print a formatted summary of the wrapped insights."""
        if "error" in wrapped:
            print(f"\n✗ Error: {wrapped['error']}")
            return
        
        print("\n" + "="*60)
        print("🎉 YOUR 2025 GARMIN WRAPPED 🎉")
        print("="*60)
        
        # Running Activities
        if wrapped.get("activities"):
            activities = wrapped["activities"]
            print(f"\n🏃 RUNNING")
            print(f"   Total Runs: {activities.get('total_runs', 0)}")
            print(f"   Distance: {activities.get('total_distance_km', 0):.2f} km")
            print(f"   Time: {activities.get('total_time_hours', 0):.2f} hours")
            print(f"   Elevation: {activities.get('total_elevation_m', 0):.0f} m")
            print(f"   Calories: {activities.get('total_calories', 0):,}")
            
            if activities.get('longest_run'):
                longest = activities['longest_run']
                print(f"\n   🏆 Longest Run: {longest['distance_km']:.2f} km")
            
            if activities.get('fastest_pace'):
                fastest = activities['fastest_pace']
                print(f"   ⚡ Fastest Pace: {fastest.get('pace_formatted', '0:00')}/km")
            
            if activities.get('averages'):
                avg = activities['averages']
                print(f"\n   📊 Avg Distance: {avg['distance_km']:.2f} km")
                print(f"   📊 Avg Pace: {avg.get('pace_formatted', '0:00')}/km")
        
        # Sleep
        if wrapped.get("sleep"):
            sleep = wrapped["sleep"]
            print(f"\n😴 SLEEP")
            if 'avg_sleep_score' in sleep:
                print(f"   Avg Sleep Score: {sleep['avg_sleep_score']}/100")
                print(f"   Best Score: {sleep['best_sleep_score']}/100")
            if 'avg_sleep_hours' in sleep:
                print(f"   Avg Sleep: {sleep['avg_sleep_hours']} hours/night")
                print(f"   Total Sleep: {sleep['total_sleep_hours']} hours")
            if 'avg_deep_sleep_hours' in sleep:
                print(f"   Avg Deep Sleep: {sleep['avg_deep_sleep_hours']} hours")
            if 'avg_rem_sleep_hours' in sleep:
                print(f"   Avg REM Sleep: {sleep['avg_rem_sleep_hours']} hours")
        
        # Stress
        if wrapped.get("stress"):
            stress = wrapped["stress"]
            print(f"\n🧘 STRESS")
            if 'avg_stress_level' in stress:
                print(f"   Avg Stress Level: {stress['avg_stress_level']}/100")
                print(f"   Lowest Day: {stress['lowest_stress_day']}/100")
                print(f"   Highest Day: {stress['highest_stress_day']}/100")
        
        # Heart Rate
        if wrapped.get("heart_rate"):
            hr = wrapped["heart_rate"]
            print(f"\n❤️  HEART RATE")
            if 'avg_resting_hr' in hr:
                print(f"   Avg Resting HR: {hr['avg_resting_hr']:.0f} bpm")
                print(f"   Lowest: {hr['lowest_resting_hr']} bpm")
                print(f"   Highest: {hr['highest_resting_hr']} bpm")
        
        # Body Battery
        if wrapped.get("body_battery"):
            bb = wrapped["body_battery"]
            print(f"\n🔋 BODY BATTERY")
            if 'avg_battery_charged' in bb:
                print(f"   Avg Charged: {bb['avg_battery_charged']:.0f} points")
                print(f"   Best Recharge: {bb['best_recharge_day']:.0f} points")
            if 'avg_battery_drained' in bb:
                print(f"   Avg Drained: {bb['avg_battery_drained']:.0f} points")
        
        # Steps
        if wrapped.get("steps"):
            steps = wrapped["steps"]
            print(f"\n👟 STEPS")
            if 'total_steps' in steps:
                print(f"   Total Steps: {steps['total_steps']:,}")
                print(f"   Avg Daily: {steps['avg_daily_steps']:,.0f}")
                print(f"   Most in a Day: {steps['most_steps_day']:,}")
                print(f"   Days Over 10k: {steps['days_over_10k']}")
        
        # VO2 Max
        if wrapped.get("vo2_max"):
            vo2 = wrapped["vo2_max"]
            print(f"\n💪 VO2 MAX")
            if 'latest_vo2_max' in vo2:
                print(f"   Latest: {vo2['latest_vo2_max']} ml/kg/min")
                print(f"   Highest: {vo2['highest_vo2_max']} ml/kg/min")
                print(f"   Average: {vo2['avg_vo2_max']} ml/kg/min")
            if 'vo2_improvement' in vo2:
                improvement = vo2['vo2_improvement']
                symbol = "📈" if improvement > 0 else "📉"
                print(f"   {symbol} Yearly Change: {improvement:+.1f} ml/kg/min ({vo2['vo2_improvement_percent']:+.1f}%)")
        
        # Training Load
        if wrapped.get("training_load"):
            tl = wrapped["training_load"]
            print("\n🎯 TRAINING LOAD")
            if 'avg_acute_training_load' in tl:
                print(f"   Avg Acute Load: {tl['avg_acute_training_load']:.0f}")
                print(f"   Highest Acute: {tl['highest_acute_load']:.0f}")
                print(f"   Latest Acute: {tl['latest_acute_load']:.0f}")
            if 'avg_chronic_training_load' in tl:
                print(f"   Avg Chronic Load: {tl['avg_chronic_training_load']:.0f}")
                print(f"   Latest Chronic: {tl['latest_chronic_load']:.0f}")
            if 'most_common_status' in tl:
                print(f"   Most Common Status: {tl['most_common_status'].replace('_', ' ').title()}")
        
        # Personal Records
        if wrapped.get("activities") and wrapped["activities"].get("personal_records"):
            print(f"\n🏆 2025 PERSONAL RECORDS")
            records = wrapped["activities"]["personal_records"]
            all_time_prs = wrapped.get("all_time_prs", {})
            
            # Distance mapping for display
            distance_names = {
                "5k": "5K",
                "10k": "10K",
                "half_marathon": "Half Marathon",
                "marathon": "Marathon"
            }
            
            for distance, record in records.items():
                if record:
                    is_all_time = self._check_if_all_time_pr(distance, record, all_time_prs)
                    all_time_marker = " 🌟 ALL-TIME PR!" if is_all_time else ""
                    
                    # Format time as HH:MM:SS
                    time_seconds = record.get('time_minutes', 0) * 60
                    time_formatted = self._format_time(time_seconds)
                    pace_formatted = record.get('pace_formatted', '0:00')
                    
                    display_name = distance_names.get(distance, distance.upper())
                    print(f"   {display_name}: {time_formatted} ({pace_formatted}/km){all_time_marker}")
        
        print("\n" + "="*60)
    
    def _check_if_all_time_pr(self, distance: str, year_record: Dict, all_time_prs: Dict) -> bool:
        """Check if a year's PR is also an all-time PR."""
        if not all_time_prs or distance not in all_time_prs:
            # If no all-time PR exists, this must be the all-time PR
            return True
        
        all_time_pr = all_time_prs[distance]
        year_time = year_record.get('time_minutes', 0) * 60  # Convert to seconds
        all_time_time = all_time_pr.get('time_seconds', 0)
        
        # Check if year time is equal to or better than all-time
        # (within 2 seconds tolerance for floating point and rounding)
        # OR if year time is faster (lower), it's a new all-time PR
        return year_time <= all_time_time + 2


# Example usage
if __name__ == "__main__":
    # Initialize
    # Replace with your credentials or use environment variables
    garmin = GarminWrapped(
        email="your_email@example.com",
        password="your_password"
    )
    
    # Generate 2025 wrapped
    wrapped = garmin.generate_wrapped_2025()
    
    # Print formatted summary
    garmin.print_wrapped_summary(wrapped)
    
    # Access specific insights programmatically
    if "error" not in wrapped:
        activities = wrapped.get("activities", {})
        sleep = wrapped.get("sleep", {})
        print(f"\n🎊 You ran {activities.get('total_distance_km', 0):.0f} km and slept {sleep.get('total_sleep_hours', 0):.0f} hours this year!")