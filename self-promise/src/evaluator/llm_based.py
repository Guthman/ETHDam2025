"""
LLM-based promise evaluator implementation.
This evaluator uses a language model to evaluate promises.
"""

import json
import datetime
from typing import Dict, Any

from .interface import PromiseEvaluator, EvaluatorRegistry


class LLMEvaluator(PromiseEvaluator):
    """
    LLM-based promise evaluator.
    
    This evaluator uses a language model to evaluate promises.
    It's suitable for promises with more complex or subjective criteria.
    """

    def __init__(self, model_name: str = "mock_llm"):
        """
        Initialize the LLM-based evaluator.
        
        Args:
            model_name: The name of the LLM model to use
        """
        self.model_name = model_name

    def evaluate(self, promise: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a promise against the provided evidence.
        
        Args:
            promise: The promise to evaluate
            evidence: The evidence to evaluate against
            
        Returns:
            A dictionary containing the evaluation result
        """
        # For the MVP, we'll use a mock LLM response
        # In a real implementation, this would call an actual LLM API

        # Format the prompt
        prompt = self._format_prompt(promise, evidence)

        # Get the LLM response
        llm_response = self._mock_llm_call(prompt, promise, evidence)

        return llm_response

    def _format_prompt(self, promise: Dict[str, Any], evidence: Dict[str, Any]) -> str:
        """
        Format the prompt for the LLM.
        
        Args:
            promise: The promise to evaluate
            evidence: The evidence to evaluate against
            
        Returns:
            The formatted prompt
        """
        # Convert the promise and evidence to a readable format
        promise_str = json.dumps(promise, indent=2)

        # Summarize the evidence to avoid overwhelming the LLM
        evidence_summary = self._summarize_evidence(evidence)

        # Create the prompt
        prompt = f"""
You are an impartial evaluator determining if a person has fulfilled their promise.

THE PROMISE:
{promise_str}

EVIDENCE SUMMARY:
{evidence_summary}

Based on the promise and the evidence provided, determine if the promise was fulfilled.
Consider the specific criteria in the promise and evaluate if the evidence shows these criteria were met.
Provide your reasoning and a confidence score (0-1) for your evaluation.

Your response should be in JSON format with the following structure:
{{
  "fulfilled": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Your detailed reasoning here",
  "details": {{
    // Any additional details about your evaluation
  }}
}}
"""

        return prompt

    def _summarize_evidence(self, evidence: Dict[str, Any]) -> str:
        """
        Summarize the evidence to avoid overwhelming the LLM.
        
        Args:
            evidence: The evidence to summarize
            
        Returns:
            A summary of the evidence
        """
        summary = []

        # Summarize exercise sessions
        exercise_sessions = evidence.get("exercise_sessions", [])
        if exercise_sessions:
            summary.append(f"Exercise Sessions: {len(exercise_sessions)} sessions found")

            # Group by week
            weeks = {}
            for session in exercise_sessions:
                start_time = datetime.datetime.fromisoformat(session.get("start_time"))
                week_start = start_time - datetime.timedelta(days=start_time.weekday())
                week_key = week_start.strftime("%Y-%m-%d")

                if week_key not in weeks:
                    weeks[week_key] = []

                weeks[week_key].append(session)

            # Summarize by week
            for week_key, sessions in weeks.items():
                summary.append(f"  Week of {week_key}: {len(sessions)} sessions")

        # Summarize elevated heart rate periods
        elevated_hr_periods = evidence.get("elevated_hr_periods", [])
        if elevated_hr_periods:
            summary.append(f"Elevated Heart Rate Periods: {len(elevated_hr_periods)} periods found")

            # Group by week
            weeks = {}
            for period in elevated_hr_periods:
                start_time = datetime.datetime.fromisoformat(period.get("start_time"))
                week_start = start_time - datetime.timedelta(days=start_time.weekday())
                week_key = week_start.strftime("%Y-%m-%d")

                if week_key not in weeks:
                    weeks[week_key] = []

                weeks[week_key].append(period)

            # Summarize by week
            for week_key, periods in weeks.items():
                avg_duration = sum(p.get("duration_minutes", 0) for p in periods) / len(periods)
                avg_hr = sum(p.get("average_heart_rate", 0) for p in periods) / len(periods)

                summary.append(
                    f"  Week of {week_key}: {len(periods)} periods, "
                    f"avg duration: {avg_duration:.1f} min, "
                    f"avg HR: {avg_hr:.1f} bpm"
                )

        return "\n".join(summary)

    def _mock_llm_call(self, prompt: str, promise: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock LLM API call.
        
        In a real implementation, this would call an actual LLM API.
        For the MVP, we'll return a mock response based on the promise type.
        
        Args:
            prompt: The prompt for the LLM
            promise: The promise to evaluate
            evidence: The evidence to evaluate against
            
        Returns:
            The LLM response
        """
        promise_type = promise.get("type", "")

        # For exercise frequency promises
        if promise_type == "exercise_frequency":
            frequency = promise.get("frequency", 1)
            period = promise.get("period", "week")

            # Count exercise sessions by period
            exercise_sessions = evidence.get("exercise_sessions", [])

            # Determine if the promise was fulfilled based on a simple heuristic
            # In a real implementation, the LLM would do a more sophisticated analysis
            fulfilled = len(exercise_sessions) >= frequency

            return {
                "fulfilled": fulfilled,
                "confidence": 0.85,  # LLM evaluations typically have lower confidence
                "reasoning": (
                    f"Based on the evidence, the user promised to exercise {frequency} times per {period} "
                    f"and the data shows {len(exercise_sessions)} exercise sessions. "
                    f"{'This meets the criteria.' if fulfilled else 'This does not meet the criteria.'}"
                ),
                "details": {
                    "sessions_found": len(exercise_sessions),
                    "required_frequency": frequency,
                    "period": period
                }
            }

        # For exercise duration promises
        elif promise_type == "exercise_duration":
            heart_rate_threshold = promise.get("heart_rate_threshold", 120)
            duration_minutes = promise.get("duration_minutes", 25)

            # Count elevated heart rate periods
            elevated_hr_periods = evidence.get("elevated_hr_periods", [])

            # Filter periods that meet the criteria
            qualifying_periods = [
                p for p in elevated_hr_periods
                if p.get("average_heart_rate", 0) >= heart_rate_threshold and
                   p.get("duration_minutes", 0) >= duration_minutes
            ]

            fulfilled = len(qualifying_periods) > 0

            return {
                "fulfilled": fulfilled,
                "confidence": 0.9,
                "reasoning": (
                    f"The user promised to maintain a heart rate above {heart_rate_threshold} bpm "
                    f"for at least {duration_minutes} minutes. "
                    f"The data shows {len(qualifying_periods)} periods meeting these criteria. "
                    f"{'This meets the criteria.' if fulfilled else 'This does not meet the criteria.'}"
                ),
                "details": {
                    "qualifying_periods": len(qualifying_periods),
                    "heart_rate_threshold": heart_rate_threshold,
                    "duration_minutes": duration_minutes
                }
            }

        # For custom promises
        else:
            # For custom promises, we'd normally rely on the LLM's reasoning
            # For the MVP, we'll return a generic response
            return {
                "fulfilled": True,  # Default to fulfilled for demo purposes
                "confidence": 0.7,
                "reasoning": (
                    "Based on the evidence provided, the user appears to have fulfilled their promise. "
                    "The data shows consistent activity patterns that align with the promise criteria."
                ),
                "details": {
                    "note": "This is a mock LLM evaluation for demonstration purposes."
                }
            }


# Register the evaluator
EvaluatorRegistry.register("llm", LLMEvaluator)
