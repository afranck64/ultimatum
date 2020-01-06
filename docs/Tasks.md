# Tasks

## Experience (exp)
Raw data:
- **ultimatum_game_experience**: Number of ultimatum games already played.
- **time_spent**: How long the user required for both reading instruction and completing the task.

## Cognitive Control (cc)
### Raw data
- **letters**: A colon separated list of letters in the order they were shown to the participant (M: signal, W: noise)
- **clicked**: A 0|1 colon separated values string with 0: user didn't clicked, 1: user clicked
- **delays**: Colon separated values, which each value being the delay to user required before clicking on the signal.
- **time_spent**: How long the user required for both reading instruction and completing the task.

## Choices (cpc)
### Raw data
- **q1, ..., q10**: Either A or B, representing the lottery the user selected.
- **time_spent**: How long the user required for both reading instruction and completing the task.


## Rathus Assertivenes Schedule (ras)
### Raw data
- **q1, ..., q3**: Int between -3 and 3, representing how likely the user consider the affirmation to be regarding himself.
- **time_spent**: How long the user required for both reading instruction and completing the task.


## Risk (risk)
### Raw data
- **q1, ..., q4**: Integer between 1 and 10 representing the lottery the user selected.
- **time_spent**: How long the user required for both reading instruction and completing the task.


## Responder (resp)
### Raw data:
- **min_offer**: The minimum offer the responder is ready to accept.
- **min_offer_final**: The final minimum offer the responder is willing to accept. In treatments where the the responder is later informed of the DSS, it contains the informed decision of the responder. (when missing, has the same value as **min_offer**)
- **resp_time_spent**: The time spent by the responder for instruction reading till submission of his decision.
 uninformed **min_offer**. (optional, when missing, has the same value as **resp_time_spent**)

## Proposer (prop)
### Raw data:
- **offer**: The proposer's offer
- **ai_offer**: (optional) AI-System's proposed offer
- **offer_final**: The proposer's offer when informed, after usage of the AI-System. (Note: in treatments T2X, this value is the same as **ai_offer** as the AI-System plays for the proposer)
*Notice:* In treatments T2X offer, offer_final and offer_dss are derived from ai_offer as the AI-System plays for the proposer.
- **prop_time_spent**: The time spent by the proposer for instruction reading till submission of his decision.