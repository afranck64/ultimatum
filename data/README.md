# README


## Files
1. Main survey form: result__survey
2. Responder main task: result__resp
3. Proposer main task: result__prop (includes resp + transformed features)
4. Features tasks:
    - Cognitive control / Letters Selection: result__cc
    - Choice prediction challenge / Choices: result__cpc
    - Experience: result__exp
    - Risk assessment: result__risk
    - Rathus assertivenes schedule / Assertiveness questinnaire: result__ras

## Tasks raw data
### Main Survey form

#### Demographics
- **gender**: Ggender
- **age**: Age range
- **ethnicity**: Colon separated values of participant reported ethnicities
- **income**: Proportion of income earned by from crowdsourcing microtasks
- **education**: Highest degree or level of school completed

#### Control questions and attention check
- **proposer**: Proposer role in the ultimatum game. Valid with the value 'correct'
- **responder**: Responder role in the ultimatum game. Valid with the value'correct'
- **proposer_responder**: Experiment desing question. Valid with value 'correct'
- **money_division**: Money division question. Valid wiht the value 'correct'
- **test**: Attention check. Valid with the value 'ball'

### Experience (exp)
- **ultimatum_game_experience**: Number of ultimatum games already played.
- **time_spent**: How long the user required for both reading instruction and completing the task.
- **worker_id**: Anonymised participant ID

### Cognitive Control (cc)
- **letters**: A colon separated list of letters in the order they were shown to the participant (M: signal, W: noise)
- **clicked**: A 0|1 colon separated values string with 0: user didn't clicked, 1: user clicked
- **delays**: Colon separated values, which each value being the delay to user required before clicking on the signal.
- **time_spent**: How long the user required for both reading instruction and completing the task.
- **worker_id**: Anonymised participant ID

### Choices (cpc)
- **q1, ..., q10**: Either A or B, representing the lottery the user selected.
- **time_spent**: How long the user required for both reading instruction and completing the task.
- **worker_id**: Anonymised participant ID


### Rathus Assertivenes Schedule (ras)
- **q1, ..., q30**: Int between -3 and 3, representing how likely the user consider the affirmation to be regarding himself.
- **time_spent**: How long the user required for both reading instruction and completing the task.
- **worker_id**: Anonymised participant ID


### Risk (risk)
- **q1, ..., q4**: Integer between 1 and 10 representing the lottery the user selected.
- **time_spent**: How long the user required for both reading instruction and completing the task.
- **worker_id**: Anonymised participant ID


### Responder (resp)
- **min_offer**: The minimum offer the responder is ready to accept.
- **min_offer_final**: The final minimum offer the responder is willing to accept. In treatments where the responder is later informed about the DSS, it contains the informed decision of the responder. (when missing, has the same value as **min_offer**)
- **resp_time_spent**: The time spent by the responder for instruction reading till submission of his decision.
 uninformed **min_offer**. (optional, when missing, has the same value as **resp_time_spent**)
- **worker_id**: Anonymised participant ID

#### Responder feedback:
- **feedback_alternative**: Participant's agreement to the affirmation: «I would have chosen a different minimum offer if the proposer did not have a recommendation system.» with 1=Strongly disagree, ..., 7=Strongly agree.
- **feedback_fairness**: Participant's agreement to the affirmation: «I think it is unfair that the proposer gets to use a recommendation system.» with 1=Strongly disagree, ..., 7=Strongly agree.
- **feedback_accuracy**: Participant's agreement to the affirmation:
    - Treatment t1x and t2x:  «On average, i think the recommendation system is xxx than the Proposer.» with 1=Worse than the Proposer, ...,  7=Better than the Proposer.
    - Treatments t30 and t31: «On average, I think the AI System will earn the human proposer more than they would be able to do themself.» with 1=Strongly disagree, ..., 7=Strongly agree.
- **feedback_ai_offers**: Participant's agreement to the affirmation: «On average, I think the AI System offers ... than a human PROPOSER.» with 1=Less and 7=More.


### Proposer (prop)
- **offer**: The proposer's offer without using the AI-System
- **dss_offer**: (optional) AI-System's proposed offer
- **offer_final**: The proposer's offer when informed, after usage of the AI-System.
- **prop_time_spent**: The time spent by the proposer for instruction reading till submission of his decision.
- **dss_calls_pauses**: Colon separated time spent between usage of the AI-System. Only unique values were considered.
- **dss_calls_offers**: Colon separated offers probed with the AI-System. Only unique values were considered.
- **dss_calls_acceptance_probabilities**: Colon separated probability of a probed offer being accepted as reported by the AI-System.
- **dss_calls_best_offer_probabilities**: Colon separated probability of a probed offer being the one mathching the responder's requested min offer as reported by the AI-System.
- **dss_calls_count_unique**: number of calls made to the AI-System wihtout considering repeated calls with the same offer
- **dss_calls_count_repeated**: number of calls made to the AI-System including repeated calls with the same offer
- **worker_id**: Anonymised participant ID

#### Proposer feedback:
- **feedback_understanding**: Participant's agreement to the the affirmation: «I could understand why the AI System thought the responder would accept a given offer.» with 1=Strongly disagree, ..., 7=Strongly agree.
- **feedback_explanation**: Participant's agreement to the the affirmation: «It is hard for me to explain how the AI-System judged my offers.» with 1=Strongly disagree and 7=Strongly agree.
- **feedback_alternative**: Participant's agreement to the the affirmation: «I would have made another offer if the RESPONDER was (NOT) informed about the AI System» with 1=Strongly disagree, ..., 7=Strongly agree.
- **feedback_accuracy**: Participant's agreement to the the affirmation: «On average, i think the recommendation system is xxx than me.» with 1=Worse than me, ...,  7=Better than me.
In treatment T10, the values correspond to participants answer to the question: «On average, recommendations of the AI System allow PROPOSERS to gain the following share of the pie left by RESPONDERS:» and values correspond to: 0=No clue, 1=0%, ..., 6=100%




