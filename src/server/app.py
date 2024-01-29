# Import necessary modules
import pyrebase
from flask import Flask, flash, redirect, render_template, request, session, abort, url_for, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from datetime import datetime
import re
import json
from collections import OrderedDict

# Create a new Flask application
app = Flask(__name__)

app.static_folder = '../../static'  # Adjust the path based on your project structure
app.static_url_path = '/static'

# Set the secret key for the Flask app. This is used for session security.
app.secret_key = "AAAApwM_ANA:APA91bF209EEGtLm_JJ9l0DIPyeHR-wAg1s8AWY5z8_s0QcHUBlS2lywJ08pJNqi5ndfWbY5C4o9c6S4KZ-Gc6nJFcs04hO_LM5b_4VYbQFsgaFSxnKT1MrWXBxX6q-CJIsj4iZHSflp"

# Configuration for Firebase
config = {
    "apiKey": "AIzaSyCaVC3BTn44PEaIGubdxDo5r3h7TFMekS4",
    "authDomain": "turtohunt.firebaseapp.com",
    "databaseURL": "https://turtohunt-default-rtdb.firebaseio.com",
    "storageBucket": "turtohunt.appspot.com"
}

# Initialize Firebase
firebase = pyrebase.initialize_app(config)

# Get reference to the auth service and database service
auth = firebase.auth()
db = firebase.database()

user_states = {}

level = []
digithistory = []
# Load messages from the JSON file
messages = {}

# Route for the login page
@app.route("/")
def login():
    return render_template("login.html")

# Route for the signup page
@app.route("/signup")
def signup():
    return render_template("signup.html")

# Route for the welcome page
@app.route("/welcome")
def welcome():
    # Check if user is logged in
    if session.get("is_logged_in", False):
        history = db.child("history").get().val()
        message_list = db.child("messages").get().val()
        json_string = json.dumps(message_list, indent=2)
        return render_template("welcome.html", email=session["email"], name=session["name"], messages=messages, historylist=history, messagelist = message_list, str_msg = json_string)
    else:
        # If user is not logged in, redirect to login page
        return redirect(url_for('login'))

# Function to check password strength
def check_password_strength(password):
    # At least one lower case letter, one upper case letter, one digit, one special character, and at least 8 characters long
    return re.match(r'^(?=.*\d)(?=.*[!@#$%^&*])(?=.*[a-z])(?=.*[A-Z]).{8,}$', password) is not None

# Route for login result
@app.route("/result", methods=["POST", "GET"])
def result():
    if request.method == "POST":
        result = request.form
        email = result["email"]
        password = result["pass"]
        try:
            # Authenticate user
            user = auth.sign_in_with_email_and_password(email, password)
            session["is_logged_in"] = True
            session["email"] = user["email"]
            session["uid"] = user["localId"]
            # Fetch user data
            data = db.child("users").get().val()
            # Update session data
            if data and session["uid"] in data:
                session["name"] = data[session["uid"]]["name"]
                # Update last login time
                db.child("users").child(session["uid"]).update({"last_logged_in": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")})
            else:
                session["name"] = "User"
            # Redirect to welcome page
            return redirect(url_for('welcome'))
        except Exception as e:
            print("Error occurred: ", e)
            return redirect(url_for('login'))
    else:
        # If user is logged in, redirect to welcome page
        if session.get("is_logged_in", False):
            return redirect(url_for('welcome'))
        else:
            return redirect(url_for('login'))

# Route for user registration
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        result = request.form
        email = result["email"]
        password = result["pass"]
        name = result["name"]
        if not check_password_strength(password):
            print("Password does not meet strength requirements")
            return redirect(url_for('signup'))
        try:
            # Create user account
            auth.create_user_with_email_and_password(email, password)
            # Authenticate user
            user = auth.sign_in_with_email_and_password(email, password)
            session["is_logged_in"] = True
            session["email"] = user["email"]
            session["uid"] = user["localId"]
            session["name"] = name
            # Save user data
            data = {"name": name, "email": email, "last_logged_in": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}
            db.child("users").child(session["uid"]).set(data)
            return redirect(url_for('welcome'))
        except Exception as e:
            print("Error occurred during registration: ", e)
            return redirect(url_for('signup'))
    else:
        # If user is logged in, redirect to welcome page
        if session.get("is_logged_in", False):
            return redirect(url_for('welcome'))
        else:
            return redirect(url_for('signup'))

# Route for password reset
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        email = request.form["email"]
        try:
            # Send password reset email
            auth.send_password_reset_email(email)
            return render_template("reset_password_done.html")  # Show a page telling user to check their email
        except Exception as e:
            print("Error occurred: ", e)
            return render_template("reset_password.html", error="An error occurred. Please try again.")  # Show error on reset password page
    else:
        return render_template("reset_password.html")  # Show the password reset page


@app.route("/submit_messages", methods=['POST', 'GET'])
def submit_messages():
    # Retrieve messages from the client-side
    client_messages = request.json.get('clientMessages', [])
    phonenumber = request.json.get('twilio_number')
    for msg in client_messages:
        current_level = messages

        # Loop through levels 0 to 4
        for level in [msg[f'level{i}'] for i in range(5) if f'level{i}' in msg]:
            current_level = current_level.setdefault(level, {})

        # Set the content at the deepest level
        current_level['content'] = msg['content']
    db.child("messages").child(phonenumber).set(messages)
    return jsonify({'success': True})

@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    """Respond to incoming phone calls with a dynamic multi-level menu."""
    call_messages = {}
    data = db.child("messages").get().val()

    to_number = request.values.get('To')
    from_number = request.values['From']
    call_status = request.values.get('CallStatus')
    
    if call_status == 'completed':
        user_state = user_states.get(from_number, {'level': 0, 'attempts': 0, 'digithistory': []})
        data = {
            "twilio": to_number,
            "Phone": from_number,
            "History Time": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            "Digit Number": user_state['digithistory'],
            "Call Status": call_status,
        }
        db.child("history").push(data)

    # Update session data
    if data and to_number in data:
        call_messages = data[to_number]
    else:
        call_messages = {"content": "A message has not been set for that number."}
    # Get the user's current state or set it to the initial state
    from_number = request.values.get('From')
    user_state = user_states.get(from_number, {'level': 0, 'attempts': 0, 'digithistory': []})

    # Check if this is a new call (first entry in the call)
    if user_state.get('call_id') != request.values.get('CallSid'):
        user_state = {'level': 0, 'attempts': 0, 'call_id': request.values.get('CallSid'), 'digithistory': []}

    # Start our TwiML response
    resp = VoiceResponse()

    if user_state['attempts'] >= 3:
        # End the call if the maximum number of attempts is reached
        resp.say("Thank you for calling. Goodbye.")
    else:
        with resp.gather(numDigits=1, action='/handle-key', method='POST') as gather:
            message = None
            if user_state['level'] == 0:
                message = call_messages
            if user_state['level'] == 1:
                message = call_messages.get(f"{level[0]}", {})
            if user_state['level'] == 2:
                message = call_messages.get(f"{level[0]}", {}).get(f"{level[1]}", {})
            if user_state['level'] == 3:
                message = call_messages.get(f"{level[0]}", {}).get(f"{level[1]}", {}).get(f"{level[2]}", {})
            if user_state['level'] == 4:
                message = call_messages.get(f"{level[0]}", {}).get(f"{level[1]}", {}).get(f"{level[2]}", {}).get(f"{level[3]}", {})
            if user_state['level'] == 5:
                message = call_messages.get(f"{level[0]}", {}).get(f"{level[1]}", {}).get(f"{level[2]}", {}).get(f"{level[3]}", {}).get(f"{level[4]}", {})
            if message:
                gather.say(message['content'], voice='Polly.Amy')

        # If user doesn't input anything, increment the attempts counter
        resp.redirect('/answer')
        user_state['attempts'] += 1

    # Update the user's state
    user_states[from_number] = user_state

    return str(resp)

@app.route("/handle-key", methods=['POST'])
def handle_key():
    """Handle key press from user."""
    digit_pressed = request.values['Digits']
    from_number = request.values['From']

    # Get the user's current state or set it to the initial state
    user_state = user_states.get(from_number, {'level': 0, 'attempts': 0, 'digithistory': []})

    if digit_pressed == '0':
        user_state['level'] -= 1
        level.pop()
    else:
        # user_state['level'] = str(max(1, int(user_state['level']) + 1))
        user_state['level'] += 1
        level.append(digit_pressed) 

    # Add the digit_pressed to the digithistory
    user_state['digithistory'].append(digit_pressed)

    resp = VoiceResponse()
    # Reset attempts counter on valid input
    user_state['attempts'] = 0

    # Update the user's state
    user_states[from_number] = user_state

    # Redirect to the answer route to continue the menu
    resp.redirect('/answer')

    return str(resp)

# Route for logout
@app.route("/logout")
def logout():
    # Update last logout time
    db.child("users").child(session["uid"]).update({"last_logged_out": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")})
    session["is_logged_in"] = False
    return redirect(url_for('login'))

