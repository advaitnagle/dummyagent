import streamlit as st
import openai
from datetime import datetime, timedelta
import os
import json

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "failed_attempts" not in st.session_state:
    st.session_state.failed_attempts = 0

# Mock order database
ORDERS = {
    "123": {"status": "shipped", "eta": (datetime.now() + timedelta(days=3)).strftime("%B %d"), "items": ["Wireless Earbuds", "Phone Case"]},
    "456": {"status": "delivered", "delivery_date": "September 15", "items": ["Smart Watch", "Charging Cable"]},
    "789": {"status": "processing", "ship_date": (datetime.now() + timedelta(days=2)).strftime("%B %d"), "items": ["Bluetooth Speaker"]}
}

# Escalation triggers
ESCALATION_KEYWORDS = ["fraud", "dispute", "human", "agent", "supervisor", "manager", "speak to someone", "real person"]

# Load your system prompt
SYSTEM_PROMPT = """
You are a helpful, professional customer support agent for an e-commerce company called "ShopEasy". 
Your role is to assist customers with their inquiries about orders, returns, shipping, and products.

Your tone should be:
- Professional but warm
- Concise but thorough
- Helpful without overpromising

When responding to customers:
1. If they ask about order status, you can check orders #123 (shipped, arriving in 3 days), #456 (delivered Sept 15), or #789 (processing, ships in 2 days). For other order numbers, apologize and offer to escalate.
2. For returns/refunds, collect the order number and reason, then confirm the return has been initiated.
3. For product questions, provide general information but acknowledge when you don't have specific details.
4. For shipping policy questions, explain that standard shipping is 3-5 business days and express is 1-2 business days.

IMPORTANT ESCALATION RULES:
- Escalate immediately if the customer mentions fraud, payment disputes, or specifically requests a human agent.
- After 2 failed attempts to understand the customer's request, offer to escalate to a human agent.
- When escalating, say: "I'll connect you with a human support agent who can better assist you with this. Please hold while I transfer your chat."

Remember to be solution-oriented and thank the customer for their patience.
"""

# Flexible LLM provider function
def get_llm_response(messages, provider="openai"):
    # Get API key from Streamlit secrets or environment variables
    api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or gpt-4 if available
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error communicating with OpenAI: {str(e)}"

def check_for_escalation(user_message):
    """Check if the message should trigger escalation to a human agent"""
    # Check for explicit escalation keywords
    if any(keyword in user_message.lower() for keyword in ESCALATION_KEYWORDS):
        return True
    
    # Check for failed attempts threshold
    if st.session_state.failed_attempts >= 2:
        st.session_state.failed_attempts = 0  # Reset counter after escalation
        return True
    
    return False

def extract_order_number(message):
    """Try to extract an order number from the message"""
    words = message.split()
    for word in words:
        # Clean up the word to check if it's an order number
        cleaned = word.strip("#.,?!").strip()
        if cleaned in ORDERS:
            return cleaned
    return None

def handle_order_status(order_number):
    """Generate a response for order status inquiries"""
    if order_number in ORDERS:
        order = ORDERS[order_number]
        if order["status"] == "shipped":
            return f"Your order #{order_number} has been shipped and is scheduled to arrive by {order['eta']}. It contains: {', '.join(order['items'])}."
        elif order["status"] == "delivered":
            return f"Your order #{order_number} was delivered on {order['delivery_date']}. It contained: {', '.join(order['items'])}."
        elif order["status"] == "processing":
            return f"Your order #{order_number} is currently processing and will ship on {order['ship_date']}. It contains: {', '.join(order['items'])}."
    return None

def handle_return_refund(order_number):
    """Generate a response for return/refund initiation"""
    if order_number in ORDERS:
        return f"I've initiated a return for order #{order_number}. You'll receive a return shipping label via email shortly. Once we receive the returned items, your refund will be processed within 5-7 business days."
    return None

def process_message(user_message):
    """Process the user message and determine an appropriate response"""
    
    # Check for escalation triggers
    if check_for_escalation(user_message):
        return "I'll connect you with a human support agent who can better assist you with this. Please hold while I transfer your chat."
    
    # Try to extract order number
    order_number = extract_order_number(user_message)
    
    # Check if this is an order status query
    if order_number and ("status" in user_message.lower() or "where" in user_message.lower() or "track" in user_message.lower()):
        response = handle_order_status(order_number)
        if response:
            return response
    
    # Check if this is a return/refund request
    if order_number and ("return" in user_message.lower() or "refund" in user_message.lower()):
        response = handle_return_refund(order_number)
        if response:
            return response
    
    # If we reach here, use the LLM for a response
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # Add conversation history
    for message in st.session_state.messages:
        messages.append({"role": message["role"], "content": message["content"]})
    
    # Add the current message
    messages.append({"role": "user", "content": user_message})
    
    # Get response from LLM
    response = get_llm_response(messages)
    
    # If the response seems generic or confused, increment the failed attempts counter
    generic_responses = [
        "I'm not sure I understand",
        "I don't have that information",
        "I'm unable to assist with that",
        "I'm not sure what you're asking",
        "Could you please clarify"
    ]
    
    if any(generic in response for generic in generic_responses):
        st.session_state.failed_attempts += 1
    else:
        st.session_state.failed_attempts = 0  # Reset on successful response
        
    return response

# Streamlit app layout
st.title("ShopEasy Customer Support")
st.markdown("Welcome to ShopEasy support! How can I help you today?")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("Type your question here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant"):
        response = process_message(prompt)
        st.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Add some helpful example queries
st.sidebar.title("Example Queries")
st.sidebar.markdown("""
- What's the status of order #123?
- I want to return my order #456
- What's your shipping policy?
- How do I track my order?
- I think there's fraud on my account
""")

# About section
st.sidebar.title("About")
st.sidebar.info("This is a demo customer support chatbot for ShopEasy e-commerce platform.")