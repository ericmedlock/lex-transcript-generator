#!/usr/bin/env python3
"""
Simple transcript generator for Amazon Lex training data.
"""

import json
import random
import datetime
from pathlib import Path

# Sample data
NAMES = ["Alex Smith", "Jordan Lee", "Taylor Brown", "Morgan Davis"]
SCENARIOS = [
    "Simple appointment booking",
    "Appointment rescheduling", 
    "Cancellation request",
    "New customer inquiry"
]

def generate_conversation(scenario, min_turns=10, max_turns=20):
    """Generate a simple conversation based on scenario."""
    turns = []
    num_turns = random.randint(min_turns, max_turns)
    
    # Start conversation
    turns.append(("User", "Hello, I'd like to schedule an appointment."))
    turns.append(("Bot", "I'd be happy to help you schedule an appointment. May I have your name?"))
    
    # Add middle turns based on scenario
    name = random.choice(NAMES)
    turns.append(("User", f"Yes, it's {name}."))
    turns.append(("Bot", f"Thank you, {name}. What type of appointment are you looking for?"))
    
    # Fill remaining turns with generic responses
    for i in range(len(turns), num_turns):
        if i % 2 == 0:  # User turn
            turns.append(("User", "That works for me."))
        else:  # Bot turn
            turns.append(("Bot", "Perfect, I'll get that set up for you."))
    
    return turns

def to_contact_lens_format(conv_id, turns):
    """Convert conversation to Contact Lens v1.1.0 format."""
    return {
        "Participants": [
            {"ParticipantId": "A1", "ParticipantRole": "AGENT"},
            {"ParticipantId": "C1", "ParticipantRole": "CUSTOMER"}
        ],
        "Version": "1.1.0",
        "ContentMetadata": {
            "RedactionTypes": ["PII"],
            "Output": "Raw"
        },
        "CustomerMetadata": {
            "ContactId": conv_id
        },
        "Transcript": [
            {
                "ParticipantId": "C1" if speaker == "User" else "A1",
                "Id": f"T{i:06d}",
                "Content": content
            }
            for i, (speaker, content) in enumerate(turns, start=1)
        ]
    }

def main():
    out_dir = Path("./transcripts")
    out_dir.mkdir(exist_ok=True)
    
    num_conversations = 10
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    for i in range(num_conversations):
        scenario = random.choice(SCENARIOS)
        turns = generate_conversation(scenario)
        conv_id = f"conv_{i+1:05d}"
        
        # Convert to Contact Lens format
        transcript = to_contact_lens_format(conv_id, turns)
        
        # Save to file
        filename = f"transcript_{conv_id}_{date_str}.json"
        with open(out_dir / filename, "w") as f:
            json.dump(transcript, f, indent=2)
    
    print(f"Generated {num_conversations} transcripts in {out_dir}")

if __name__ == "__main__":
    main()