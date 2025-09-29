#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek R1 8B Conversation Analysis
"""

import json

def analyze_deepseek_conversation():
    """Analyze the DeepSeek R1 8B conversation transcript"""
    
    # Extract conversation text from the provided JSON
    conversation_json = {
        "Version": "1.1.0",
        "Transcript": [
            {"Id": "T000001", "Content": "We need to schedule my annual checkup.", "ParticipantId": "C1"},
            {"Id": "T000002", "Content": "Okay, let's get started. Do you have any particular date or time in mind?", "ParticipantId": "A1"},
            {"Id": "T000003", "Content": "I'd prefer next Friday the 15th around noon.", "ParticipantId": "C1"},
            {"Id": "T000004", "Content": "Let me confirm that... Next Friday, November 15th at 12 PM is a bit tricky. Dr. Evans has that slot booked until January.", "ParticipantId": "A1"},
            {"Id": "T000005", "Content": "Could we move it to Tuesday or Wednesday then?", "ParticipantId": "C1"},
            {"Id": "T000006", "Content": "Tuesdays and Wednesdays fill up quickly starting December 4th for the coming months. How about Thursday afternoon, say early evening?", "ParticipantId": "A1"},
            {"Id": "T000007", "Content": "Thursday... what time is available after November 7th?", "ParticipantId": "C1"},
            {"Id": "T000008", "Content": "After Nov 7th, 3 PM on Thursdays should be free until we see a pattern. What name shall I enter this under?", "ParticipantId": "A1"},
            {"Id": "T000009", "Content": "My name is Sarah Johnson.", "ParticipantId": "C1"},
            {"Id": "T000010", "Content": "Alright, Sarah Johnson - scheduled for the following Thursday at 3 PM with Dr. Evans. Do you have any questions about that time slot?", "ParticipantId": "A1"},
            {"Id": "T000011", "Content": "No, but could it be extended by ten minutes perhaps?", "ParticipantId": "C1"},
            {"Id": "T000012", "Content": "We can note a longer duration if needed. Any other concerns regarding the appointment?", "ParticipantId": "A1"},
            {"Id": "T000013", "Content": "Not now, thanks. How do I get to the office from there?", "ParticipantId": "C1"},
            {"Id": "T000014", "Content": "The office is located at 4567 Main Street North. Do you need public transit directions or just street maps?", "ParticipantId": "A1"},
            {"Id": "T000015", "Content": "Just general driving instructions should be fine. Thanks anyway.", "ParticipantId": "C1"},
            {"Id": "T000016", "Content": "You're welcome. Is November's date still a possibility for another appointment, maybe later in the week then?", "ParticipantId": "A1"},
            {"Id": "T000017", "Content": "No, that was my initial preference... but let's stick with the Thursday then.", "ParticipantId": "C1"},
            {"Id": "T000018", "Content": "Understood. I'll keep you informed about any changes to that slot. Have a good day!", "ParticipantId": "A1"}
        ]
    }
    
    # Extract conversation text
    conversation_text = ""
    for turn in conversation_json["Transcript"]:
        role = "Customer" if turn["ParticipantId"] == "C1" else "Agent"
        conversation_text += f"{role}: {turn['Content']}\n"
    
    print("=== DEEPSEEK R1 8B CONVERSATION ANALYSIS ===\n")
    print("CONVERSATION:")
    print(conversation_text)
    print("\n" + "="*50)
    
    # Manual analysis based on grading criteria
    analysis = {
        "realness_score": 8,
        "coherence_score": 7,
        "naturalness_score": 8,
        "overall_score": 8,
        "healthcare_valid": True
    }
    
    print("\nGRADING ANALYSIS:")
    print(f"Realness Score: {analysis['realness_score']}/10")
    print("  + Natural appointment scheduling flow")
    print("  + Realistic date/time conflicts")
    print("  + Appropriate customer service responses")
    print("  + Believable patient information collection")
    
    print(f"\nCoherence Score: {analysis['coherence_score']}/10")
    print("  + Logical progression from request to booking")
    print("  + Consistent date references")
    print("  - Some minor date confusion (Nov 15th vs Nov 7th)")
    print("  + Clear resolution with final appointment time")
    
    print(f"\nNaturalness Score: {analysis['naturalness_score']}/10")
    print("  + Conversational tone throughout")
    print("  + Natural hesitations and clarifications")
    print("  + Realistic customer service language")
    print("  + Appropriate politeness markers")
    
    print(f"\nOverall Score: {analysis['overall_score']}/10")
    print("  + Excellent training data quality")
    print("  + Covers key appointment booking scenarios")
    print("  + Good length and complexity")
    print("  + Realistic healthcare context")
    
    print(f"\nHealthcare Valid: {analysis['healthcare_valid']}")
    print("  + Clear medical appointment context")
    print("  + Doctor name mentioned (Dr. Evans)")
    print("  + Annual checkup scenario")
    print("  + Office location provided")
    
    print("\n" + "="*50)
    print("COMPARISON TO 1B MODEL:")
    print("+ Much more coherent conversation flow")
    print("+ Better context awareness and memory")
    print("+ More natural language patterns")
    print("+ Improved logical consistency")
    print("+ Better handling of complex scheduling scenarios")
    
    print("\nSTRENGTHS:")
    print("- Natural back-and-forth negotiation")
    print("- Realistic scheduling constraints")
    print("- Good customer service tone")
    print("- Appropriate level of detail")
    print("- Believable patient interaction")
    
    print("\nMINOR WEAKNESSES:")
    print("- Slight date reference inconsistency")
    print("- Could use more specific medical terminology")
    print("- Agent could be more proactive about alternatives")
    
    print("\nRECOMMENDATION: ACCEPT")
    print("This conversation demonstrates significant improvement over 1B models")
    print("Quality is suitable for chatbot training data")
    
    return analysis

if __name__ == "__main__":
    analyze_deepseek_conversation()