#!/usr/bin/env python3
"""
LEX Format Converter - Convert various conversation formats to Amazon LEX Contact Lens format
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

class LexConverter:
    """Convert conversations to Amazon LEX Contact Lens v1.1.0 format"""
    
    def __init__(self):
        self.version = "1.1.0"
    
    def convert_to_lex(self, conversation_data: Dict[str, Any], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Convert conversation data to LEX Contact Lens format
        
        Args:
            conversation_data: Raw conversation data
            metadata: Optional metadata to include
            
        Returns:
            LEX-formatted conversation
        """
        # Generate unique IDs
        conversation_id = str(uuid.uuid4())
        
        # Detect format and convert
        if self._is_lex_format(conversation_data):
            return conversation_data
        elif self._is_simple_format(conversation_data):
            return self._convert_simple_format(conversation_data, conversation_id, metadata)
        elif self._is_transcript_array(conversation_data):
            return self._convert_transcript_array(conversation_data, conversation_id, metadata)
        else:
            # Try to extract from various formats
            return self._convert_generic_format(conversation_data, conversation_id, metadata)
    
    def _is_lex_format(self, data: Dict) -> bool:
        """Check if data is already in LEX format"""
        required_fields = ["Participants", "Version", "ContentMetadata", "Transcript"]
        return all(field in data for field in required_fields)
    
    def _is_simple_format(self, data: Dict) -> bool:
        """Check if data is in simple conversation format"""
        return "conversation" in data or "turns" in data or "messages" in data
    
    def _is_transcript_array(self, data: Dict) -> bool:
        """Check if data contains a transcript array"""
        return "transcript" in data and isinstance(data["transcript"], list)
    
    def _convert_simple_format(self, data: Dict, conv_id: str, metadata: Optional[Dict]) -> Dict[str, Any]:
        """Convert simple conversation format to LEX"""
        # Extract conversation turns
        turns = []
        conversation_text = data.get("conversation", data.get("content", ""))
        
        if conversation_text:
            # Parse conversation text into turns
            lines = conversation_text.strip().split('\n')
            turn_id = 1
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect speaker patterns
                if line.startswith(("Agent:", "Staff:", "Receptionist:", "Doctor:")):
                    participant_id = "AGENT"
                    content = line.split(":", 1)[1].strip()
                elif line.startswith(("User:", "Patient:", "Customer:", "Caller:")):
                    participant_id = "CUSTOMER"
                    content = line.split(":", 1)[1].strip()
                else:
                    # Default to alternating pattern
                    participant_id = "AGENT" if turn_id % 2 == 1 else "CUSTOMER"
                    content = line
                
                turns.append({
                    "Id": str(turn_id),
                    "ParticipantId": participant_id,
                    "Content": content,
                    "BeginOffsetMillis": turn_id * 1000,
                    "EndOffsetMillis": (turn_id + 1) * 1000
                })
                turn_id += 1
        
        return self._build_lex_structure(turns, conv_id, metadata)
    
    def _convert_transcript_array(self, data: Dict, conv_id: str, metadata: Optional[Dict]) -> Dict[str, Any]:
        """Convert transcript array format to LEX"""
        transcript = data["transcript"]
        turns = []
        
        for i, turn in enumerate(transcript, 1):
            if isinstance(turn, dict):
                participant_id = turn.get("speaker", turn.get("role", "AGENT" if i % 2 == 1 else "CUSTOMER"))
                content = turn.get("text", turn.get("content", turn.get("message", "")))
            else:
                # String format
                participant_id = "AGENT" if i % 2 == 1 else "CUSTOMER"
                content = str(turn)
            
            # Normalize participant ID
            if participant_id.upper() in ["AGENT", "STAFF", "RECEPTIONIST", "DOCTOR"]:
                participant_id = "AGENT"
            elif participant_id.upper() in ["CUSTOMER", "PATIENT", "USER", "CALLER"]:
                participant_id = "CUSTOMER"
            
            turns.append({
                "Id": str(i),
                "ParticipantId": participant_id,
                "Content": content,
                "BeginOffsetMillis": i * 1000,
                "EndOffsetMillis": (i + 1) * 1000
            })
        
        return self._build_lex_structure(turns, conv_id, metadata)
    
    def _convert_generic_format(self, data: Dict, conv_id: str, metadata: Optional[Dict]) -> Dict[str, Any]:
        """Convert generic format by extracting text content"""
        # Try to find conversation content in various fields
        content_fields = ["content", "text", "conversation", "dialogue", "transcript"]
        conversation_text = ""
        
        for field in content_fields:
            if field in data and data[field]:
                conversation_text = str(data[field])
                break
        
        if not conversation_text:
            # Use the entire data as text
            conversation_text = json.dumps(data, indent=2)
        
        # Create a simple format and convert
        simple_data = {"conversation": conversation_text}
        return self._convert_simple_format(simple_data, conv_id, metadata)
    
    def _build_lex_structure(self, turns: List[Dict], conv_id: str, metadata: Optional[Dict]) -> Dict[str, Any]:
        """Build the complete LEX Contact Lens structure"""
        # Ensure we have both participants
        participant_ids = set(turn["ParticipantId"] for turn in turns)
        
        participants = []
        if "AGENT" in participant_ids:
            participants.append({
                "ParticipantId": "AGENT",
                "ParticipantRole": "AGENT"
            })
        if "CUSTOMER" in participant_ids:
            participants.append({
                "ParticipantId": "CUSTOMER", 
                "ParticipantRole": "CUSTOMER"
            })
        
        # If no participants found, create defaults
        if not participants:
            participants = [
                {"ParticipantId": "AGENT", "ParticipantRole": "AGENT"},
                {"ParticipantId": "CUSTOMER", "ParticipantRole": "CUSTOMER"}
            ]
        
        # Build LEX structure
        lex_data = {
            "Version": self.version,
            "Channel": "VOICE",
            "AccountId": "123456789012",
            "InstanceId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "ContactId": conv_id,
            "InitialContactId": conv_id,
            "PreviousContactId": None,
            "InitiationMethod": "INBOUND",
            "SystemEndpoint": {
                "Type": "TELEPHONE_NUMBER",
                "Address": "+12345678901"
            },
            "CustomerEndpoint": {
                "Type": "TELEPHONE_NUMBER", 
                "Address": "+19876543210"
            },
            "MediaStreams": [
                {
                    "Type": "AUDIO",
                    "StorageType": "S3",
                    "MediaProperties": {
                        "AudioProperties": {
                            "AudioCodec": "PCM",
                            "AudioSampleRate": 8000
                        }
                    }
                }
            ],
            "Participants": participants,
            "ContentMetadata": {
                "Output": "Raw"
            },
            "CustomerMetadata": metadata or {},
            "Transcript": turns
        }
        
        return lex_data
    
    def validate_lex_format(self, lex_data: Dict[str, Any]) -> bool:
        """Validate LEX format compliance"""
        required_fields = ["Participants", "Version", "ContentMetadata", "CustomerMetadata", "Transcript"]
        
        # Check top-level fields
        for field in required_fields:
            if field not in lex_data:
                return False
        
        # Check participants
        participants = lex_data.get("Participants", [])
        if not participants:
            return False
        
        participant_ids = set()
        for participant in participants:
            if "ParticipantId" not in participant or "ParticipantRole" not in participant:
                return False
            if participant["ParticipantRole"] not in ["AGENT", "CUSTOMER"]:
                return False
            participant_ids.add(participant["ParticipantId"])
        
        # Check transcript
        transcript = lex_data.get("Transcript", [])
        if not transcript:
            return False
        
        for turn in transcript:
            if "ParticipantId" not in turn or "Id" not in turn or "Content" not in turn:
                return False
            if turn["ParticipantId"] not in participant_ids:
                return False
        
        return True