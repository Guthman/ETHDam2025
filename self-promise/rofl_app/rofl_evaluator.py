import json
import argparse
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def evaluate_active_zone_minutes_promise(promise_params: dict, evidence: dict) -> dict:
    """
    Evaluates a promise based on achieving a target number of Active Zone Minutes.

    Args:
        promise_params: A dictionary containing promise parameters.
                        Expected keys:
                        - "target_active_zone_minutes" (int): The target AZM.
                        - "promise_period_days" (int): The period of the promise in days.
        evidence: A dictionary containing the achieved evidence.
                  Expected keys:
                  - "total_active_zone_minutes_achieved" (int): AZM achieved in the period.

    Returns:
        A dictionary with evaluation results:
        - "fulfilled" (bool): True if the promise is met, False otherwise.
        - "reasoning" (str): An explanation of the evaluation outcome.
        - "achieved_azm" (int): The actual AZM achieved.
        - "target_azm" (int): The target AZM.
    """
    try:
        target_azm = int(promise_params.get("target_active_zone_minutes", 0))
        # promise_period_days is for context but not directly used in this simple evaluation
        # as evidence is assumed to be pre-aggregated for the period.
        promise_period_days = int(promise_params.get("promise_period_days", 0))

        achieved_azm = int(evidence.get("total_active_zone_minutes_achieved", 0))

        logging.info(
            "Evaluating promise: target_azm=%(target_azm)d, achieved_azm=%(achieved_azm)d, period_days=%(promise_period_days)d",
            {
                "target_azm": target_azm,
                "achieved_azm": achieved_azm,
                "promise_period_days": promise_period_days
            }
        )

        if achieved_azm >= target_azm:
            fulfilled = True
            reasoning = (
                f"Promise fulfilled: Achieved {achieved_azm} out of "
                f"{target_azm} target Active Zone Minutes."
            )
        else:
            fulfilled = False
            reasoning = (
                f"Promise not fulfilled: Achieved {achieved_azm} out of "
                f"{target_azm} target Active Zone Minutes. "
                f"Short by {target_azm - achieved_azm} minutes."
            )

        return {
            "fulfilled": fulfilled,
            "reasoning": reasoning,
            "achieved_azm": achieved_azm,
            "target_azm": target_azm
        }

    except ValueError as e:
        logging.error("ValueError during evaluation: %(error)s", {"error": e})
        return {
            "fulfilled": False,
            "reasoning": f"Error in processing parameters or evidence: {e}",
            "achieved_azm": 0,
            "target_azm": promise_params.get("target_active_zone_minutes", 0)
        }
    except Exception as e:
        logging.error("Unexpected error during evaluation: %(error)s", {"error": e})
        return {
            "fulfilled": False,
            "reasoning": f"An unexpected error occurred: {e}",
            "achieved_azm": 0,
            "target_azm": promise_params.get("target_active_zone_minutes", 0)
        }


def main():
    """
    Main function to parse arguments, call the evaluator, and print results.
    """
    parser = argparse.ArgumentParser(
        description="ROFL Rule-Based Evaluator for Self-Promise (Fitbit AZM)."
    )
    parser.add_argument(
        '--promise_params_json',
        type=str,
        required=True,
        help='JSON string of promise parameters. E.g., \'{"target_active_zone_minutes": 150, "promise_period_days": 7}\''
    )
    parser.add_argument(
        '--evidence_json',
        type=str,
        required=True,
        help='JSON string of user evidence (mocked Fitbit data). E.g., \'{"total_active_zone_minutes_achieved": 160}\''
    )

    args = parser.parse_args()

    try:
        promise_params = json.loads(args.promise_params_json)
        evidence = json.loads(args.evidence_json)
    except json.JSONDecodeError as e:
        logging.error("Failed to decode JSON input: %(error)s", {"error": e})
        # Output a JSON error message that can be parsed by the ROFL service if needed
        print(json.dumps({
            "fulfilled": False,
            "reasoning": f"Invalid JSON input: {e}",
            "achieved_azm": 0,
            "target_azm": 0
        }))
        return

    evaluation_result = evaluate_active_zone_minutes_promise(promise_params, evidence)

    # Output result as a JSON string to stdout
    print(json.dumps(evaluation_result))


if __name__ == '__main__':
    main()
