"""
Evaluator interface for promise evaluation.
This defines the common interface for all evaluator implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class PromiseEvaluator(ABC):
    """
    Abstract base class for promise evaluators.
    
    All evaluator implementations must implement this interface.
    """
    
    @abstractmethod
    def evaluate(self, promise: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a promise against the provided evidence.
        
        Args:
            promise: The promise to evaluate
            evidence: The evidence to evaluate against
            
        Returns:
            A dictionary containing the evaluation result:
            {
                "fulfilled": bool,  # Whether the promise was fulfilled
                "confidence": float,  # Confidence in the evaluation (0-1)
                "reasoning": str,  # Explanation of the evaluation
                "details": Dict  # Additional details about the evaluation
            }
        """
        pass


class EvaluatorRegistry:
    """
    Registry for promise evaluators.
    
    This allows for pluggable evaluator implementations.
    """
    
    _evaluators = {}
    
    @classmethod
    def register(cls, name: str, evaluator_class):
        """
        Register an evaluator implementation.
        
        Args:
            name: The name of the evaluator
            evaluator_class: The evaluator class
        """
        cls._evaluators[name] = evaluator_class
    
    @classmethod
    def get_evaluator(cls, name: str, **kwargs) -> Optional[PromiseEvaluator]:
        """
        Get an evaluator implementation by name.
        
        Args:
            name: The name of the evaluator
            **kwargs: Additional arguments to pass to the evaluator constructor
            
        Returns:
            An instance of the evaluator, or None if not found
        """
        evaluator_class = cls._evaluators.get(name)
        if evaluator_class:
            return evaluator_class(**kwargs)
        return None
    
    @classmethod
    def list_evaluators(cls) -> List[str]:
        """
        List all registered evaluators.
        
        Returns:
            A list of evaluator names
        """
        return list(cls._evaluators.keys())
