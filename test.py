import os
import json
from flask import Flask, render_template, request, jsonify
from langchain.chains import LLMChain
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
import markdown
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Get Groq API key
groq_api_key = os.getenv("GROQ_API")

model = 'llama3-8b-8192'

# Initialize Groq Langchain chat object and conversation
groq_chat = ChatGroq(
        groq_api_key=groq_api_key, 
        model_name=model
)

with open('steps.json', 'r') as file:
    assessment_data = json.load(file)

# Get system prompt from JSON
system_prompt = assessment_data['system_prompt']
conversational_memory_length = 20  # Number of previous messages the chatbot will remember during the conversation
memory = ConversationBufferWindowMemory(k=conversational_memory_length, memory_key="chat_history", return_messages=True)

UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_question = request.json.get('question')
    
    if user_question:
        # Construct a chat prompt template using various components
        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{human_input}")
            ]
        )

        # Create a conversation chain
        conversation = LLMChain(
            llm=groq_chat,
            prompt=prompt,
            verbose=False,
            memory=memory,
        )

        response = conversation.predict(human_input=user_question)
        response_markdown = markdown.markdown(response)

        # Extract BP reading and treatment status from the user's input or conversation history
        bp_reading = extract_bp_reading(user_question)
        is_on_treatment = extract_treatment_status(memory.chat_memory)

        # Evaluate blood pressure based on JSON rules
        evaluation_response = evaluate_blood_pressure(bp_reading, is_on_treatment)

        # Return the formatted response with evaluation
        return jsonify({"answer": response_markdown + "<br><br>" + evaluation_response})

    return jsonify({"answer": "Sorry, I didn't understand that."})

def extract_bp_reading(user_input):
    """Extracts systolic and diastolic blood pressure from the user's input."""
    try:
        # Assume user input follows the format "SYS/DIA"
        parts = user_input.split('/')
        sys = int(parts[0])
        dia = int(parts[1])
        return sys, dia
    except (ValueError, IndexError):
        return None  # If unable to extract BP, return None

def extract_treatment_status(chat_history):
    """Extracts treatment status from the conversation history."""
    for message in reversed(chat_history):
        if "anti-hypertensive treatment" in message["content"].lower():
            if "yes" in message["content"].lower():
                return True
            elif "no" in message["content"].lower():
                return False
    return None  # If treatment status is not found, return None

def evaluate_blood_pressure(bp_reading, is_on_treatment):
    """Evaluates the blood pressure based on the provided readings and treatment status."""
    if bp_reading is None or is_on_treatment is None:
        return "Unable to evaluate blood pressure. Please provide the correct readings and treatment status."
    
    sys, dia = bp_reading
    if is_on_treatment:
        if sys >= 160 or dia >= 110:
            return "Your blood pressure is very high. Sit quietly for 5 minutes and repeat the blood pressure reading. If this is a repeat reading in the severe range, contact your local hospital’s maternity unit immediately and go in for an urgent assessment today at the local hospital."
        elif 150 <= sys <= 159 or 100 <= dia <= 109:
            return "Your blood pressure is high. Sit quietly for 5 minutes and repeat the blood pressure reading. If this is a repeat reading in the high range, contact your provider urgently and arrange assessment today."
        elif 140 <= sys <= 149 or 90 <= dia <= 99:
            return "Your blood pressure is raised. No change in your medication yet."
        elif 130 <= sys <= 139 or 80 <= dia <= 89:
            return "Your blood pressure is in the target range when on treatment. This is fine provided that you have no side effects."
        elif 100 <= sys <= 129 and dia < 80:
            return "Your blood pressure is normal but you may require less treatment. Follow your medication change instructions if your blood pressure remains in this range for 2 days in a row."
        elif sys < 100 and dia < 80:
            return "Your blood pressure is too low. Sit quietly for 5 minutes and repeat the blood pressure reading. If this is a repeat reading in the low range, contact your provider urgently and arrange assessment today."
    else:
        if sys >= 160 or dia >= 110:
            return "Your blood pressure is very high. Sit quietly for 5 minutes and repeat the blood pressure reading. If this is a repeat reading in the severe range, immediately contact your local hospital’s maternity unit for urgent assessment today at the hospital."
        elif 140 <= sys <= 159 or 90 <= dia <= 109:
            return "Your blood pressure is high. Sit quietly for 5 minutes and repeat the blood pressure reading. If 2 or more consecutive readings are in this high range, contact your provider or local hospital’s maternity assessment unit for review within 48 hours."
        elif sys < 140 and dia < 90:
            return "Your blood pressure is normal."
    
    return "Unable to evaluate blood pressure. Please ensure the readings are correct."

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
