AI_FEEDBACK_SCALAS = {
    1: "Strongly disagree",
    2: "",
    3: "",
    4: "",
    5: "",
    6: "",
    7: "Strongly agree"
}

AI_FEEDBACK_ACCURACY_SCALAS = {
    "no_clue": "I don't know",
    "0_percent": "0%",
    "20_percent": "20%",
    "40_percent": "40%",
    "60_percent": "60%",
    "80_percent": "80%",
    "100_percent": "100%",
}


AI_FEEDBACK_ACCURACY_PROPOSER_SCALAS = {
    "ai_much_worse": "Worse than me",
    "ai_worse": "",
    "ai_sligthly_worse": "",
    "ai_equal_to_proposer": "As good as me",
    "ai_slighly_better": "",
    "ai_better": "",
    "ai_much_better": "Better than me",
}

AI_FEEDBACK_ACCURACY_RESPONDER_SCALAS = {
    "ai_much_worse": "Worse than the PROPOSER",
    "ai_worse": "",
    "ai_sligthly_worse": "",
    "ai_equal_to_proposer": "As good as the PROPOSER",
    "ai_slighly_better": "",
    "ai_better": "",
    "ai_much_better": "Better than the PROPOSER",
}

AI_SYSTEM_DESCRIPTION_BRIEF_STANDALONE_PROPOSER = """Thank you for your offer. You will now make another decision as a PROPOSER. This time you have the option to use an AI Recommendation System (AI System) to help you decide which offer to make. The system was trained using prior interactions of comparable bargaining situations."""

AI_SYSTEM_DESCRIPTION_BRIEF_PROPOSER = """Thank you for your offer. You will now make another decision as a PROPOSER. This time you have the option to use an AI Recommendation System (AI System) to help you decide which offer to make."""

AI_SYSTEM_RESPONDER_INFORMATION_PROPOSER = """The RESPONDER doesn't know about the existence of the AI-System."""

AI_SYSTEM_DESCRIPTION_EXTENDED_ACC_PROPOSER = """The system was trained using 100 prior interactions of comparable bargaining situations.
- The system learned a fixed optimal offer (AI_OFFER).
- AI_OFFER was found by testing each possible offer on comparable bargaining situations and was selected as the one that provided the highest average gain to PROPOSERs.
- Following the AI System's recommendations, PROPOSERs can gain 80% of the pie left by RESPONDERs.
- Following the AI System's recommendations, PROPOSERs can have 95% of their offers accepted.
- The probability of an offer being accepted is higher than 50% when the offer is greater than or equal to AI_OFFER.
- The probability of an offer being the RESPONDER's minimal offer is higher the closer the offer is to AI_OFFER."""

AI_SYSTEM_DESCRIPTION_EXTENDED_PROPOSER =  """The system was trained using 100 prior interactions of comparable bargaining situations.
- The system learned a fixed optimal offer (AI_OFFER).
- AI_OFFER was found by testing each possible offer on these prior bargaining situations and was selected as the one that provided the highest average gain to PROPOSERs.
- Using the same process, the system also constructed an interval that judges offers that deviate from its recommendation."""



AI_SYSTEM_DESCRIPTION_USAGE_PROPOSER = """To use the AI System, simply select a test offer and submit it to the system. The system will tell you its estimates on:
1. The probability that your offer will be accepted by your specific RESPONDER.
2. The probability that your offer is the minimal offer accepted by your specific RESPONDER.

You can use the system as often as you want."""

AI_SYSTEM_DESCRIPTION_BRIEF_STANDALONE_RESPONDER = """Thank you for your minimum offer. You will now make another decision as a RESPONDER. This time your PROPOSER has the option to use an AI Recommendation System (AI System) to help him/her decide which offer to make.
The system was trained using prior interactions of comparable bargaining situations."""

AI_SYSTEM_DESCRIPTION_BRIEF_RESPONDER = """Thank you for your minimum offer. You will now make another decision as a RESPONDER. This time your PROPOSER has the option to use an AI Recommendation System (AI System) to help him/her decide which offer to make."""

AI_SYSTEM_DESCRIPTION_EXTENDED_RESPONDER = AI_SYSTEM_DESCRIPTION_EXTENDED_PROPOSER


AI_SYSTEM_AUTO_DESCRIPTION_BRIEF_STANDALONE_RESPONDER = """An AI Machine-Learning System will autonomously make an offer to you on behalf of a human PROPOSER. The system was trained using prior interactions of comparable bargaining situations. The human PROPOSER does not make any decisions, he/she only receives whatever money the system earns from this task."""

AI_SYSTEM_AUTO_DESCRIPTION_BRIEF_RESPONDER = """An AI Machine-Learning System will autonomously make an offer to you on behalf of a human PROPOSER. The human PROPOSER does not make any decisions, he/she only receives whatever money the system earns from this task."""

AI_SYSTEM_AUTO_DESCRIPTION_EXTENDED_RESPONDER = """The system was trained using 100 prior interactions of comparable bargaining situations.
- The system learned a fixed optimal offer (AI_OFFER).
- AI_OFFER was found by testing each possible offer on these prior bargaining situations and was selected as the one that provided the highest average gain to PROPOSERs.
- Using the same process, the system also constructed an interval that judges offers that deviate from its recommendation."""
