"""Unit tests for ConfidenceScorer."""
import pytest
from infrastructure.confidence.scorer import ConfidenceScorer


class TestConfidenceScorer:
    """Test confidence scoring logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = ConfidenceScorer()
    
    def test_no_patch_generated(self):
        """Test scoring when no patch was generated."""
        result = self.scorer.calculate_confidence({
            'patch_generated': False
        })
        
        assert result['confidence_score'] == 0
        assert result['risk_rating'] == 'High'
        assert 'No patch generated' in result['factors']['reason']
    
    def test_high_confidence_low_risk(self):
        """Test high confidence with validation passed."""
        result = self.scorer.calculate_confidence({
            'patch_generated': True,
            'triage_score': 10,
            'complexity': 'low',
            'validation_passed': True,
            'repair_attempts': 0
        })
        
        assert result['confidence_score'] >= 85
        assert result['risk_rating'] == 'Low'
    
    def test_low_confidence_high_risk(self):
        """Test low confidence with validation failed."""
        result = self.scorer.calculate_confidence({
            'patch_generated': True,
            'triage_score': 3,
            'complexity': 'high',
            'validation_passed': False,
            'repair_attempts': 3
        })
        
        assert result['confidence_score'] < 50
        assert result['risk_rating'] == 'High'
    
    def test_medium_confidence(self):
        """Test medium confidence scenario."""
        result = self.scorer.calculate_confidence({
            'patch_generated': True,
            'triage_score': 7,
            'complexity': 'medium',
            'validation_passed': False,
            'repair_attempts': 1
        })
        
        assert 45 <= result['confidence_score'] <= 60
        assert result['risk_rating'] in ['Medium', 'High']
    
    def test_recommendation_high_confidence(self):
        """Test recommendation for high confidence patches."""
        result = self.scorer.calculate_confidence({
            'patch_generated': True,
            'triage_score': 9,
            'complexity': 'low',
            'validation_passed': True,
            'repair_attempts': 0
        })
        
        recommendation = self.scorer.get_recommendation(result)
        assert 'auto-merge' in recommendation.lower() or 'high confidence' in recommendation.lower()
    
    def test_recommendation_low_confidence(self):
        """Test recommendation for low confidence patches."""
        result = self.scorer.calculate_confidence({
            'patch_generated': True,
            'triage_score': 2,
            'complexity': 'high',
            'validation_passed': False,
            'repair_attempts': 2
        })
        
        recommendation = self.scorer.get_recommendation(result)
        assert 'manual review' in recommendation.lower() or 'low confidence' in recommendation.lower()
    
    def test_complexity_scoring(self):
        """Test complexity affects score correctly."""
        base_data = {
            'patch_generated': True,
            'triage_score': 5,
            'validation_passed': True,
            'repair_attempts': 0
        }
        
        low_result = self.scorer.calculate_confidence({**base_data, 'complexity': 'low'})
        med_result = self.scorer.calculate_confidence({**base_data, 'complexity': 'medium'})
        high_result = self.scorer.calculate_confidence({**base_data, 'complexity': 'high'})
        
        assert low_result['confidence_score'] > med_result['confidence_score']
        assert med_result['confidence_score'] > high_result['confidence_score']
    
    def test_validation_weight(self):
        """Test that validation has highest weight."""
        passed_data = {
            'patch_generated': True,
            'triage_score': 5,
            'complexity': 'medium',
            'validation_passed': True,
            'repair_attempts': 1
        }
        
        failed_data = {**passed_data, 'validation_passed': False}
        
        passed_result = self.scorer.calculate_confidence(passed_data)
        failed_result = self.scorer.calculate_confidence(failed_data)
        
        # Validation failure should cause significant drop (35% weight)
        assert passed_result['confidence_score'] - failed_result['confidence_score'] > 20
