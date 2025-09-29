"""Conversation metadata extraction module"""

from typing import Dict, Any, List
from dataclasses import dataclass
from .format_detector import ConversationData

@dataclass
class ConversationMetadata:
    turn_count: int
    speaker_count: int
    avg_turn_length: float
    total_length: int
    speakers: List[str]
    conversation_type: str
    quality_indicators: Dict[str, Any]
    source_file: str

class MetadataExtractor:
    """Extract metadata from conversation data"""
    
    def extract_conversation_metadata(self, conversation: ConversationData) -> ConversationMetadata:
        """Extract comprehensive metadata from conversation"""
        
        turns = conversation.turns
        speakers = conversation.speakers
        
        # Basic metrics
        turn_count = len(turns)
        speaker_count = len(speakers)
        
        # Text analysis
        turn_lengths = []
        total_length = 0
        
        for turn in turns:
            text = turn.get('text', '')
            length = len(text.split()) if text else 0
            turn_lengths.append(length)
            total_length += length
        
        avg_turn_length = sum(turn_lengths) / len(turn_lengths) if turn_lengths else 0
        
        # Conversation type detection
        conversation_type = self._detect_conversation_type(conversation)
        
        # Quality indicators
        quality_indicators = self._analyze_quality(conversation)
        
        return ConversationMetadata(
            turn_count=turn_count,
            speaker_count=speaker_count,
            avg_turn_length=avg_turn_length,
            total_length=total_length,
            speakers=speakers,
            conversation_type=conversation_type,
            quality_indicators=quality_indicators,
            source_file=conversation.source_file
        )
    
    def _detect_conversation_type(self, conversation: ConversationData) -> str:
        """Detect conversation type based on patterns"""
        turns = conversation.turns
        speakers = conversation.speakers
        
        # Simple heuristics
        if len(speakers) == 1:
            return "monologue"
        elif len(speakers) == 2:
            return "dialogue"
        else:
            return "multi_party"
    
    def _analyze_quality(self, conversation: ConversationData) -> Dict[str, Any]:
        """Analyze conversation quality indicators"""
        turns = conversation.turns
        
        # Quality metrics
        empty_turns = sum(1 for turn in turns if not turn.get('text', '').strip())
        very_short_turns = sum(1 for turn in turns if len(turn.get('text', '').split()) < 2)
        
        # Speaker alternation
        speaker_sequence = [turn.get('speaker', 'unknown') for turn in turns]
        alternation_score = self._calculate_alternation_score(speaker_sequence)
        
        # Completeness
        completeness_score = 1.0 - (empty_turns / len(turns)) if turns else 0.0
        
        return {
            'completeness': completeness_score,
            'alternation_score': alternation_score,
            'empty_turns': empty_turns,
            'very_short_turns': very_short_turns,
            'has_timestamps': any('timestamp' in turn for turn in turns),
            'has_confidence': any('confidence' in turn for turn in turns)
        }
    
    def _calculate_alternation_score(self, speaker_sequence: List[str]) -> float:
        """Calculate how well speakers alternate (0-1 score)"""
        if len(speaker_sequence) < 2:
            return 1.0
        
        alternations = 0
        for i in range(1, len(speaker_sequence)):
            if speaker_sequence[i] != speaker_sequence[i-1]:
                alternations += 1
        
        max_alternations = len(speaker_sequence) - 1
        return alternations / max_alternations if max_alternations > 0 else 1.0