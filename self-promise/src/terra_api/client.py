"""
Mock implementation of Terra API client for fitness data.
This simulates the data that would be retrieved from a real fitness tracking API.
"""

import datetime
import random
import json
from typing import Dict, List, Optional, Tuple, Union


class TerraApiClient:
    """
    Mock Terra API client for retrieving fitness data.
    
    In a real implementation, this would connect to the Terra API
    and retrieve actual fitness data. For the MVP, we simulate this data.
    """
    
    def __init__(self, user_id: str):
        """
        Initialize the Terra API client.
        
        Args:
            user_id: The ID of the user to retrieve data for
        """
        self.user_id = user_id
        self._mock_data_cache = {}
    
    def get_heart_rate_data(self, 
                           start_date: datetime.datetime, 
                           end_date: datetime.datetime) -> List[Dict]:
        """
        Get heart rate data for a specific time period.
        
        Args:
            start_date: The start date/time for the data
            end_date: The end date/time for the data
            
        Returns:
            A list of heart rate data points
        """
        # Check if we have cached data for this time period
        cache_key = f"{start_date.isoformat()}_{end_date.isoformat()}"
        if cache_key in self._mock_data_cache:
            return self._mock_data_cache[cache_key]
        
        # Generate mock data
        data = self._generate_mock_heart_rate_data(start_date, end_date)
        
        # Cache the data
        self._mock_data_cache[cache_key] = data
        
        return data
    
    def _generate_mock_heart_rate_data(self, 
                                      start_date: datetime.datetime, 
                                      end_date: datetime.datetime) -> List[Dict]:
        """
        Generate mock heart rate data for a specific time period.
        
        Args:
            start_date: The start date/time for the data
            end_date: The end date/time for the data
            
        Returns:
            A list of heart rate data points
        """
        data = []
        
        # Generate data points at 1-minute intervals
        current_time = start_date
        while current_time <= end_date:
            # Generate a realistic heart rate based on time of day
            hour = current_time.hour
            
            # Base heart rate (resting: 60-80)
            base_hr = random.randint(60, 80)
            
            # Adjust for time of day
            if 6 <= hour < 9:  # Morning exercise
                hr = random.randint(100, 160)
            elif 17 <= hour < 20:  # Evening exercise
                hr = random.randint(100, 150)
            else:  # Normal daily activities
                hr = base_hr + random.randint(-5, 20)
            
            data.append({
                "timestamp": current_time.isoformat(),
                "heart_rate": hr,
                "source": "mock_terra_api"
            })
            
            # Move to next minute
            current_time += datetime.timedelta(minutes=1)
        
        return data
    
    def get_exercise_sessions(self, 
                             start_date: datetime.datetime, 
                             end_date: datetime.datetime) -> List[Dict]:
        """
        Get exercise sessions for a specific time period.
        
        Args:
            start_date: The start date/time for the data
            end_date: The end date/time for the data
            
        Returns:
            A list of exercise sessions
        """
        # Generate mock exercise sessions
        sessions = []
        
        # Determine how many days are in the range
        days = (end_date - start_date).days + 1
        
        # Generate 3-5 exercise sessions per week
        num_sessions = int(days / 7 * random.randint(3, 5))
        
        for _ in range(num_sessions):
            # Random day and time within the range
            random_days = random.randint(0, days - 1)
            random_hour = random.choice([7, 8, 17, 18, 19])  # Common exercise times
            
            session_date = start_date + datetime.timedelta(days=random_days)
            session_start = datetime.datetime(
                session_date.year, 
                session_date.month, 
                session_date.day, 
                random_hour, 
                random.randint(0, 30)
            )
            
            # Session duration between 30 and 90 minutes
            duration_minutes = random.randint(30, 90)
            session_end = session_start + datetime.timedelta(minutes=duration_minutes)
            
            # Only include if within the requested range
            if session_start >= start_date and session_end <= end_date:
                sessions.append({
                    "start_time": session_start.isoformat(),
                    "end_time": session_end.isoformat(),
                    "duration_minutes": duration_minutes,
                    "activity_type": random.choice(["running", "cycling", "walking", "strength_training"]),
                    "calories_burned": random.randint(200, 600),
                    "average_heart_rate": random.randint(120, 160),
                    "source": "mock_terra_api"
                })
        
        return sessions
    
    def check_continuous_elevated_heart_rate(self, 
                                           threshold: int, 
                                           min_duration_minutes: int,
                                           start_date: datetime.datetime, 
                                           end_date: datetime.datetime) -> List[Dict]:
        """
        Check for periods of continuously elevated heart rate.
        
        Args:
            threshold: The heart rate threshold (e.g., 120 bpm)
            min_duration_minutes: Minimum duration in minutes (e.g., 25 minutes)
            start_date: The start date/time for the data
            end_date: The end date/time for the data
            
        Returns:
            A list of periods with continuously elevated heart rate
        """
        # Get heart rate data
        hr_data = self.get_heart_rate_data(start_date, end_date)
        
        # Find periods of elevated heart rate
        elevated_periods = []
        current_period_start = None
        
        for i, data_point in enumerate(hr_data):
            hr = data_point["heart_rate"]
            timestamp = datetime.datetime.fromisoformat(data_point["timestamp"])
            
            if hr >= threshold:
                # Start a new period if not already in one
                if current_period_start is None:
                    current_period_start = timestamp
            else:
                # End the current period if there was one
                if current_period_start is not None:
                    period_duration = (timestamp - current_period_start).total_seconds() / 60
                    
                    if period_duration >= min_duration_minutes:
                        elevated_periods.append({
                            "start_time": current_period_start.isoformat(),
                            "end_time": timestamp.isoformat(),
                            "duration_minutes": period_duration,
                            "average_heart_rate": self._calculate_average_hr(
                                hr_data, 
                                current_period_start, 
                                timestamp
                            )
                        })
                    
                    current_period_start = None
        
        # Check if we're still in an elevated period at the end of the data
        if current_period_start is not None:
            last_timestamp = datetime.datetime.fromisoformat(hr_data[-1]["timestamp"])
            period_duration = (last_timestamp - current_period_start).total_seconds() / 60
            
            if period_duration >= min_duration_minutes:
                elevated_periods.append({
                    "start_time": current_period_start.isoformat(),
                    "end_time": last_timestamp.isoformat(),
                    "duration_minutes": period_duration,
                    "average_heart_rate": self._calculate_average_hr(
                        hr_data, 
                        current_period_start, 
                        last_timestamp
                    )
                })
        
        return elevated_periods
    
    def _calculate_average_hr(self, 
                             hr_data: List[Dict], 
                             start_time: datetime.datetime, 
                             end_time: datetime.datetime) -> float:
        """
        Calculate the average heart rate for a specific time period.
        
        Args:
            hr_data: The heart rate data
            start_time: The start time
            end_time: The end time
            
        Returns:
            The average heart rate
        """
        relevant_data = [
            d["heart_rate"] for d in hr_data 
            if start_time <= datetime.datetime.fromisoformat(d["timestamp"]) <= end_time
        ]
        
        if not relevant_data:
            return 0
        
        return sum(relevant_data) / len(relevant_data)


# Helper functions for testing

def generate_test_data_for_week(user_id: str, week_start: datetime.datetime) -> Dict:
    """
    Generate test data for a week.
    
    Args:
        user_id: The user ID
        week_start: The start date of the week
        
    Returns:
        A dictionary with test data
    """
    client = TerraApiClient(user_id)
    week_end = week_start + datetime.timedelta(days=7)
    
    return {
        "heart_rate_data": client.get_heart_rate_data(week_start, week_end),
        "exercise_sessions": client.get_exercise_sessions(week_start, week_end),
        "elevated_hr_periods": client.check_continuous_elevated_heart_rate(
            threshold=120,
            min_duration_minutes=25,
            start_date=week_start,
            end_date=week_end
        )
    }


def save_test_data(data: Dict, filename: str) -> None:
    """
    Save test data to a JSON file.
    
    Args:
        data: The data to save
        filename: The filename to save to
    """
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    # Generate test data for the current week
    today = datetime.datetime.now()
    week_start = today - datetime.timedelta(days=today.weekday())
    week_start = datetime.datetime(week_start.year, week_start.month, week_start.day)
    
    test_data = generate_test_data_for_week("test_user_123", week_start)
    save_test_data(test_data, "test_fitness_data.json")
    
    print(f"Generated test data with {len(test_data['heart_rate_data'])} heart rate data points")
    print(f"Found {len(test_data['exercise_sessions'])} exercise sessions")
    print(f"Detected {len(test_data['elevated_hr_periods'])} periods of elevated heart rate")
