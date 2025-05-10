"""
Rule-based promise evaluator implementation.
This evaluator uses predefined rules to evaluate promises.
"""

import datetime
from typing import Dict, Any, List

from .interface import PromiseEvaluator, EvaluatorRegistry


class RuleBasedEvaluator(PromiseEvaluator):
    """
    Rule-based promise evaluator.
    
    This evaluator uses predefined rules to evaluate promises.
    It's suitable for promises with clear, deterministic criteria.
    """

    def __init__(self):
        """Initialize the rule-based evaluator."""
        self.rule_handlers = {
            "exercise_frequency": self._evaluate_exercise_frequency,
            "exercise_duration": self._evaluate_exercise_duration,
            "exercise_consistency": self._evaluate_exercise_consistency,
        }

    def evaluate(self, promise: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a promise against the provided evidence.
        
        Args:
            promise: The promise to evaluate
            evidence: The evidence to evaluate against
            
        Returns:
            A dictionary containing the evaluation result
        """
        promise_type = promise.get("type")

        if promise_type not in self.rule_handlers:
            return {
                "fulfilled": False,
                "confidence": 0.0,
                "reasoning": f"Unknown promise type: {promise_type}",
                "details": {}
            }

        # Call the appropriate rule handler
        return self.rule_handlers[promise_type](promise, evidence)

    def _evaluate_exercise_frequency(self, promise: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an exercise frequency promise.
        
        Example promise:
        {
            "type": "exercise_frequency",
            "frequency": 3,  # Number of times per period
            "period": "week",  # Period (day, week, month)
            "start_date": "2023-01-01",
            "end_date": "2023-06-30"
        }
        
        Args:
            promise: The promise to evaluate
            evidence: The evidence to evaluate against
            
        Returns:
            A dictionary containing the evaluation result
        """
        # Extract promise parameters
        frequency = promise.get("frequency", 1)
        period = promise.get("period", "week")
        start_date = datetime.datetime.fromisoformat(promise.get("start_date"))
        end_date = datetime.datetime.fromisoformat(promise.get("end_date"))

        # Extract evidence
        exercise_sessions = evidence.get("exercise_sessions", [])

        # Group sessions by period
        periods = self._group_by_period(exercise_sessions, period, start_date, end_date)

        # Check if each period meets the frequency requirement
        fulfilled_periods = 0
        total_periods = len(periods)

        details = {
            "periods": [],
            "total_periods": total_periods,
            "fulfilled_periods": 0
        }

        for period_start, sessions in periods.items():
            period_end = self._get_period_end(period_start, period)

            period_fulfilled = len(sessions) >= frequency
            fulfilled_periods += 1 if period_fulfilled else 0

            details["periods"].append({
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "sessions_count": len(sessions),
                "required_count": frequency,
                "fulfilled": period_fulfilled
            })

        details["fulfilled_periods"] = fulfilled_periods

        # Calculate fulfillment percentage
        fulfillment_percentage = fulfilled_periods / total_periods if total_periods > 0 else 0

        # Determine if the promise was fulfilled
        fulfilled = fulfillment_percentage >= 1.0

        return {
            "fulfilled": fulfilled,
            "confidence": 1.0,  # Rule-based evaluation has high confidence
            "reasoning": (
                f"The promise required exercising {frequency} times per {period}. "
                f"You met this requirement in {fulfilled_periods} out of {total_periods} {period}s "
                f"({fulfillment_percentage:.0%})."
            ),
            "details": details
        }

    def _evaluate_exercise_duration(self, promise: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an exercise duration promise.
        
        Example promise:
        {
            "type": "exercise_duration",
            "heart_rate_threshold": 120,  # Minimum heart rate
            "duration_minutes": 25,  # Minimum duration in minutes
            "frequency": 1,  # Number of times per period
            "period": "week",  # Period (day, week, month)
            "start_date": "2023-01-01",
            "end_date": "2023-06-30"
        }
        
        Args:
            promise: The promise to evaluate
            evidence: The evidence to evaluate against
            
        Returns:
            A dictionary containing the evaluation result
        """
        # Extract promise parameters
        heart_rate_threshold = promise.get("heart_rate_threshold", 120)
        duration_minutes = promise.get("duration_minutes", 25)
        frequency = promise.get("frequency", 1)
        period = promise.get("period", "week")
        start_date = datetime.datetime.fromisoformat(promise.get("start_date"))
        end_date = datetime.datetime.fromisoformat(promise.get("end_date"))

        # Extract evidence
        elevated_hr_periods = evidence.get("elevated_hr_periods", [])

        # Filter periods that meet the criteria
        qualifying_periods = [
            p for p in elevated_hr_periods
            if p.get("average_heart_rate", 0) >= heart_rate_threshold and
               p.get("duration_minutes", 0) >= duration_minutes
        ]

        # Group qualifying periods by period
        periods = self._group_by_period(qualifying_periods, period, start_date, end_date,
                                        timestamp_key="start_time")

        # Check if each period meets the frequency requirement
        fulfilled_periods = 0
        total_periods = len(periods)

        details = {
            "periods": [],
            "total_periods": total_periods,
            "fulfilled_periods": 0,
            "qualifying_sessions": len(qualifying_periods)
        }

        for period_start, sessions in periods.items():
            period_end = self._get_period_end(period_start, period)

            period_fulfilled = len(sessions) >= frequency
            fulfilled_periods += 1 if period_fulfilled else 0

            details["periods"].append({
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "qualifying_sessions": len(sessions),
                "required_count": frequency,
                "fulfilled": period_fulfilled
            })

        details["fulfilled_periods"] = fulfilled_periods

        # Calculate fulfillment percentage
        fulfillment_percentage = fulfilled_periods / total_periods if total_periods > 0 else 0

        # Determine if the promise was fulfilled
        fulfilled = fulfillment_percentage >= 1.0

        return {
            "fulfilled": fulfilled,
            "confidence": 1.0,
            "reasoning": (
                f"The promise required exercising with a heart rate above {heart_rate_threshold} bpm "
                f"for at least {duration_minutes} minutes, {frequency} times per {period}. "
                f"You met this requirement in {fulfilled_periods} out of {total_periods} {period}s "
                f"({fulfillment_percentage:.0%})."
            ),
            "details": details
        }

    @staticmethod
    def _evaluate_exercise_consistency(promise: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an exercise consistency promise.
        
        Example promise:
        {
            "type": "exercise_consistency",
            "max_gap_days": 7,  # Maximum number of days between exercise sessions
            "start_date": "2023-01-01",
            "end_date": "2023-06-30"
        }
        
        Args:
            promise: The promise to evaluate
            evidence: The evidence to evaluate against
            
        Returns:
            A dictionary containing the evaluation result
        """
        # Extract promise parameters
        max_gap_days = promise.get("max_gap_days", 7)
        start_date = datetime.datetime.fromisoformat(promise.get("start_date"))
        end_date = datetime.datetime.fromisoformat(promise.get("end_date"))

        # Extract evidence
        exercise_sessions = evidence.get("exercise_sessions", [])

        # Sort sessions by start time
        sorted_sessions = sorted(
            exercise_sessions,
            key=lambda s: datetime.datetime.fromisoformat(s.get("start_time"))
        )

        # Find gaps larger than max_gap_days
        gaps = []
        last_session_end = start_date

        for session in sorted_sessions:
            session_start = datetime.datetime.fromisoformat(session.get("start_time"))

            # Calculate gap in days
            gap_days = (session_start - last_session_end).days

            if gap_days > max_gap_days:
                gaps.append({
                    "gap_start": last_session_end.isoformat(),
                    "gap_end": session_start.isoformat(),
                    "gap_days": gap_days
                })

            session_end = datetime.datetime.fromisoformat(session.get("end_time"))
            last_session_end = session_end

        # Check for gap from last session to end date
        final_gap_days = (end_date - last_session_end).days
        if final_gap_days > max_gap_days:
            gaps.append({
                "gap_start": last_session_end.isoformat(),
                "gap_end": end_date.isoformat(),
                "gap_days": final_gap_days
            })

        # Determine if the promise was fulfilled
        fulfilled = len(gaps) == 0

        details = {
            "max_gap_days": max_gap_days,
            "gaps_found": len(gaps),
            "gaps": gaps
        }

        return {
            "fulfilled": fulfilled,
            "confidence": 1.0,
            "reasoning": (
                f"The promise required never going more than {max_gap_days} days without exercise. "
                f"{'No gaps were found.' if fulfilled else f'Found {len(gaps)} gaps exceeding {max_gap_days} days.'}"
            ),
            "details": details
        }

    def _group_by_period(self,
                         items: List[Dict[str, Any]],
                         period: str,
                         start_date: datetime.datetime,
                         end_date: datetime.datetime,
                         timestamp_key: str = "start_time") -> Dict[datetime.datetime, List[Dict[str, Any]]]:
        """
        Group items by period (day, week, month).
        
        Args:
            items: The items to group
            period: The period to group by (day, week, month)
            start_date: The start date
            end_date: The end date
            timestamp_key: The key to use for the timestamp
            
        Returns:
            A dictionary mapping period start dates to lists of items
        """
        periods = {}

        # Generate all periods in the date range
        current_date = start_date
        while current_date <= end_date:
            period_start = self._get_period_start(current_date, period)
            periods[period_start] = []

            # Move to the next period
            if period == "day":
                current_date += datetime.timedelta(days=1)
            elif period == "week":
                current_date += datetime.timedelta(days=7)
            elif period == "month":
                # Move to the first day of the next month
                if current_date.month == 12:
                    current_date = datetime.datetime(current_date.year + 1, 1, 1)
                else:
                    current_date = datetime.datetime(current_date.year, current_date.month + 1, 1)

        # Group items by period
        for item in items:
            item_date = datetime.datetime.fromisoformat(item.get(timestamp_key))
            period_start = self._get_period_start(item_date, period)

            if period_start in periods:
                periods[period_start].append(item)

        return periods

    @staticmethod
    def _get_period_start(date: datetime.datetime, period: str) -> datetime.datetime:
        """
        Get the start date of the period containing the given date.
        
        Args:
            date: The date
            period: The period (day, week, month)
            
        Returns:
            The start date of the period
        """
        if period == "day":
            return datetime.datetime(date.year, date.month, date.day)
        elif period == "week":
            # Start of the week (Monday)
            return date - datetime.timedelta(days=date.weekday())
        elif period == "month":
            # Start of the month
            return datetime.datetime(date.year, date.month, 1)

        # Default to the date itself
        return date

    @staticmethod
    def _get_period_end(period_start: datetime.datetime, period: str) -> datetime.datetime:
        """
        Get the end date of the period.
        
        Args:
            period_start: The start date of the period
            period: The period (day, week, month)
            
        Returns:
            The end date of the period
        """
        if period == "day":
            return period_start + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
        elif period == "week":
            return period_start + datetime.timedelta(days=7) - datetime.timedelta(microseconds=1)
        elif period == "month":
            # End of the month
            if period_start.month == 12:
                next_month = datetime.datetime(period_start.year + 1, 1, 1)
            else:
                next_month = datetime.datetime(period_start.year, period_start.month + 1, 1)

            return next_month - datetime.timedelta(microseconds=1)

        # Default to the end of the day
        return period_start + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)


# Register the evaluator
EvaluatorRegistry.register("rule_based", RuleBasedEvaluator)
