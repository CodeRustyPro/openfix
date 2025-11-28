"""Base agent class for all OpenFix agents."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import uuid
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all agents in the OpenFix system."""
    
    def __init__(self, config: Dict[str, Any], run_id: Optional[str] = None):
        """
        Initialize the agent.
        
        Args:
            config: Configuration dictionary for this agent
            run_id: Optional run ID for tracking (generates new if not provided)
        """
        self.config = config
        self.run_id = run_id or str(uuid.uuid4())
        self.logger = self._setup_logger()
        self.metrics = {}
        
    def _setup_logger(self) -> logging.Logger:
        """Set up structured logging for the agent."""
        logger = logging.getLogger(f"{self.__class__.__name__}-{self.run_id[:8]}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """
        Main execution method for the agent.
        
        Args:
            input_data: Input data for the agent
            
        Returns:
            Output data from the agent
        """
        pass
    
    def log_metric(self, key: str, value: Any):
        """Log a metric for this agent run."""
        self.metrics[key] = value
        self.logger.info(f"Metric: {key}={value}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics for this agent run."""
        return {
            "agent": self.__class__.__name__,
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat(),
            **self.metrics
        }
