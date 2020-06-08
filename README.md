# Baseball Bot

A slack bot that you can talk to and play the baseball game described [here](https://www.hackster.io/hyun-woo-park/baseball-game-daecdd). The bot uses Flask, the Events API, and Python WebClient. 

## Getting Started
By running `python3 app.py` you will be starting a server locally on `localhost:3000` which will receive requests from Slack using the Events API (the exception being the slash command) via ngrok. To set this all up, you will also need to create a new app for your workspace at [api.slack.com].

### Local Setup 
1. Consider creating a virtual envinronment. Make sure you have and are using python3 and pip. Then run the following to install dependencies:
```pip install -r requirements.txt```

2. To run the application locally, you will need to tunnel requests from Slack through a public URL. To do this, you can install [ngrok](https://ngrok.com/) and then run:
```./ngrok http 3000```
3000 is the default port for this application. ngrok will create a public url for you. Save it for later

### Setup on [api.slack.com]
1. Got to [api.slack.com] and click "Create an App". Follow the prompts.
2. Click OAuth & Permissions. Add the following Bot Token Scopes:
    * channels:history
    * chat:write
    * commands
    * groups:history
    * im:history

    Click "Install App to Workspace". Follow the prompts. Copy the Bot User Oauth Access Token displayed at the end and save it as an environment variable: 
    ```export SLACK_BOT_TOKEN='xoxo-xxxxxxxxxxxxxxxxxxxxxxxxxx'```
3. Click Basic Information. Copy the Signing Secret and save as an environment variable:
    ```export SLACK_SIGNING_SECRET='xxxxxxxxxxxxxxxxxx'```
4. Click Event Subscriptions. Enter the public URL for your app (in this setup, created using ngrok above) for the Request URL. MAKE SURE to append '/slack/events' to the end of your public url. Slack should immediately show the url as verified.
5. Under Subscribe to Bot Events, add:
    * message.channels
    * message.groups
    * message.im
    This will have Slack send requests to you public url whenever these events occur.
6. Click Save Changes

## Usage
Either in a channel where you have invited Baseball Bot or a DM, enter `/start offense` or `/start defense` to start a new game with Baseball Bot.
* If playing offensively, Baseball Bot will randomly generate a number. Enter three digit numbers and Baseball Bot will respond with the number of strikes (number of digits you guessed correctly and in the correct position) and number of balls (number of digits you guessed that exist in the correct number, but are not in the correct position). If none of your digits exist in the correct number, you will be told "Out" and if guess the correct number, you will get 3 strikes and the game ends.
* If playing defensively, Baseball Bot will guess numbers and you must respond with the number of strikes and balls. Use the format `X strikes and Y balls`

## Reference
* https://github.com/slackapi/python-slackclient/tree/master/tutorial
* https://api.slack.com/bot-users

## Notes
* Make sure your SSL Certificates are up to date

