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
conversational_memory_length = 20  # number of previous messages the chatbot will remember during the conversation and
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
                SystemMessage(content=f"{system_prompt}\nEvaluation rules: {json.dumps(assessment_data['steps']['blood_pressure_evaluation'])}"),
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

        # Return the formatted response
        return jsonify({"answer": response_markdown})
        # return jsonify({"answer": response})

    return jsonify({"answer": "Sorry, I didn't understand that."})

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8000)