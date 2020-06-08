import os
import logging
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from flask import abort, Flask, jsonify, request
from slack.signature.verifier import SignatureVerifier
from urllib.parse import parse_qs
from slack.errors import SlackApiError
import random
import ssl as ssl_lib
import certifi

ssl_context = ssl_lib.create_default_context(cafile=certifi.where())

# Initialize a Flask app to host the events adapter
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ["SLACK_SIGNING_SECRET"], "/slack/events", app)
sigVerifier = SignatureVerifier(os.environ["SLACK_SIGNING_SECRET"])

# Initialize a Web API client
slack_web_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'], ssl=ssl_context)

# Saved Game States. Since data is stored in memory, game states will be lost if server restarts. 
# Keys: (team_id, channel_id, user_id) tuples. 
# Values: {"side": "defense", "numbers" : ("234", "002", "999")} OR {"side": "offense", "numbers" : "083"}
# TODO: Persist to disk
game_states = dict()


# Handles '/start' slash command by starting a new game for that unique team, channel, user. 
@app.route('/start', methods=['POST'])
def start():
    print("start called \n")
    if not (sigVerifier.is_valid_request(request.get_data(), request.headers)):
        abort(500)


    data = request.form
    side = request.form['text'].lower()
    key = (data['team_id'], data['channel_id'], data['user_id'])
    if key in game_states:
        print("starting new game...")
    
    text = create_new_game(key, side)
    if not text:
        text = "I don't understand. Please use the format '/start offense' or '/start defense'"
    
    return jsonify(
        response_type='in_channel',
        text=text
    )

# Given a KEY for GAME_STATES, and SIDE (either "offense" or "defense"), creates a new game. Overwrites if existing game exists
def create_new_game(key: tuple, side: str):
    random_num = "".join([str(random.randint(0, 9)) for i in range(3)]) # generates 3 digit number as a str
    text = None

    if side == "offense":
        game_states[key] = {"side": side, "numbers": random_num}
        text = "ok. "
    elif side == "defense":
        game_states[key] = {"side": side, "numbers": (random_num)}
        text = "ok. " + random_num

    return text

def start_onboarding(user_id: str, channel: str):
    print ("nani")
    # # Create a new onboarding tutorial.
    # onboarding_tutorial = OnboardingTutorial(channel)

    # # Get the onboarding message payload
    # message = onboarding_tutorial.get_message_payload()

    # # Post the onboarding message in Slack
    # response = slack_web_client.chat_postMessage(**message)

    # # Capture the timestamp of the message we've just posted so
    # # we can use it to update the message after a user
    # # has completed an onboarding task.
    # onboarding_tutorial.timestamp = response["ts"]

    # # Store the message sent in onboarding_tutorials_sent
    # if channel not in onboarding_tutorials_sent:
    #     onboarding_tutorials_sent[channel] = {}
    # onboarding_tutorials_sent[channel][user_id] = onboarding_tutorial


# ================ Team Join Event =============== #
# When the user first joins a team, the type of the event will be 'team_join'.
# Here we'll link the onboarding_message callback to the 'team_join' event.
@slack_events_adapter.on("team_join")
def onboarding_message(payload):
    """Create and send an onboarding welcome message to new users. Save the
    time stamp of this message so we can update this message in the future.
    """
    event = payload.get("event", {})

    # Get the id of the Slack user associated with the incoming event
    user_id = event.get("user", {}).get("id")

    # Open a DM with the new user.
    response = slack_web_client.im_open(user=user_id)
    channel = response["channel"]["id"]

    # Post the onboarding message.
    start_onboarding(user_id, channel)


# ============= Reaction Added Events ============= #
# When a users adds an emoji reaction to the onboarding message,
# the type of the event will be 'reaction_added'.
# Here we'll link the update_emoji callback to the 'reaction_added' event.
@slack_events_adapter.on("reaction_added")
def update_emoji(payload):
    """Update the onboarding welcome message after receiving a "reaction_added"
    event from Slack. Update timestamp for welcome message as well.
    """
    event = payload.get("event", {})

    channel_id = event.get("item", {}).get("channel")
    user_id = event.get("user")

    if channel_id not in onboarding_tutorials_sent:
        return

    # Get the original tutorial sent.
    onboarding_tutorial = onboarding_tutorials_sent[channel_id][user_id]

    # Mark the reaction task as completed.
    onboarding_tutorial.reaction_task_completed = True

    # Get the new message payload
    message = onboarding_tutorial.get_message_payload()

    # Post the updated message in Slack
    updated_message = slack_web_client.chat_update(**message)

    # Update the timestamp saved on the onboarding tutorial object
    onboarding_tutorial.timestamp = updated_message["ts"]


# =============== Pin Added Events ================ #
# When a users pins a message the type of the event will be 'pin_added'.
# Here we'll link the update_pin callback to the 'reaction_added' event.
@slack_events_adapter.on("pin_added")
def update_pin(payload):
    """Update the onboarding welcome message after receiving a "pin_added"
    event from Slack. Update timestamp for welcome message as well.
    """
    event = payload.get("event", {})

    channel_id = event.get("channel_id")
    user_id = event.get("user")

    # Get the original tutorial sent.
    onboarding_tutorial = onboarding_tutorials_sent[channel_id][user_id]

    # Mark the pin task as completed.
    onboarding_tutorial.pin_task_completed = True

    # Get the new message payload
    message = onboarding_tutorial.get_message_payload()

    # Post the updated message in Slack
    updated_message = slack_web_client.chat_update(**message)

    # Update the timestamp saved on the onboarding tutorial object
    onboarding_tutorial.timestamp = updated_message["ts"]


# Handler for any message that is sent to any channel the bot is a member of.
@slack_events_adapter.on("message")
def message(payload):
    print("message called \n")
    event = payload.get("event", {})
    channel_id = event.get("channel")
    key = (payload.get("team_id"), channel_id, event.get("user"))

    if key not in game_states or event.get("text")[0] == "/": 
        return
    else:
        if game_states[key]["side"] == "offense":
            text = offense(key, event.get("text"))
        elif game_states[key]["side"] == "defense":
            text = defense(key, event.get("text"))

    if text == None:
        text = "Oops, something went wrong. Try using '/start offense' or '/start defense' to start a new game!"
            
    try:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=text)
        print("sent message")
    except SlackApiError as e:
        print(f"Got an error: {e.response['error']}")

# Creates the str message we want to respond with if we are playing an offensive game with the game specified by KEY
def offense(key: tuple, guess: str):
    if not (guess.strip().isnumeric() and len(guess) == 3):
        return
    
    goal = game_states[key]["numbers"]
    balls = 0
    strikes = 0

    # Note if the player guesses the same digit twice, but that digit only appears once, 
    # it is possible to get 2 balls OR 1 ball & 1 strike. Same logic applies to guessing 3 of the same digit
    for i in range(3):
        if guess[i] == goal[i]:
            strikes += 1
        elif guess[i] in goal:
            balls += 1
        
    text = ""
    if strikes > 0:
        if strikes == 3:
            text = str(strikes) + " strikes! Congratulations!"
            del game_states[key] # remove game when player wins
        else:
            text = str(strikes) + " strike"
    if balls > 0:
        if text:
            text += " and "
        text += str(balls) + " ball"
    if not text:
        text = "Out. No matches."

    return text

# Creates the str message we want to respond with if we are playing an defensive game with the game specified by KEY
# TODO: Implement smarter guessing
# TODO: Handle if player spells out 1, 2, or 3
# TODO: Implement better parsing (possibly regex)
def defense(key: tuple, guess: str):
    guess = guess.lower()
    if "strike" not in guess and "ball" not in guess and "out" not in "guess":
        return

    words = guess.split()
    strikes = None
    balls = None
    for i, word in enumerate(words):
        if i == 0:
            continue
        if word == "strike" or word == "strikes":
            strikes = words[i - 1]
        elif word == "ball" or word == "balls":
            balls = words[i - 1]
    if strikes == 3 or strikes == "three":
        del game_states[key] # remove game when computer wins
        return
    
    return "".join([str(random.randint(0, 9)) for i in range(3)]) # generates 3 digit number as a str



        

if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    app.run(port=3000)





    