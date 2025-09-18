import streamlit as st
import openai
from datetime import datetime, timedelta
import os

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "failed_attempts" not in st.session_state:
    st.session_state.failed_attempts = 0

# Mock order database (keeping original functionality)
ORDERS = {
    "123": {"status": "shipped", "eta": (datetime.now() + timedelta(days=3)).strftime("%B %d"), "items": ["Wireless Earbuds", "Phone Case"]},
    "456": {"status": "delivered", "delivery_date": "September 15", "items": ["Smart Watch", "Charging Cable"]},
    "789": {"status": "processing", "ship_date": (datetime.now() + timedelta(days=2)).strftime("%B %d"), "items": ["Bluetooth Speaker"]}
}

# Escalation triggers
ESCALATION_KEYWORDS = ["fraud", "dispute", "human", "agent", "supervisor", "manager", "speak to someone", "real person"]

# Product data in JSON format
PRODUCT_DATA = """
{
  "products": [
    {
      "product_name": "pTron Wired Earphones - Blue Edition",
      "discounted_price": "594",
      "actual_price": "661",
      "discount_percentage": "10",
      "rating": "4.8",
      "rating_count": "464",
      "about_product": "pTron Wired Earphones in Blue. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Premium feel, sturdy build quality and excellent noise cancellation. | Crystal clear audio, good for calls and music both. | Very comfortable for long use and the battery life is great. | Battery drains too quickly, very disappointing. | Uncomfortable to wear for long periods of time."
    },
    {
      "product_name": "pTron Wireless Headphones - Grey Edition",
      "discounted_price": "15948",
      "actual_price": "19935",
      "discount_percentage": "20",
      "rating": "2.6",
      "rating_count": "4096",
      "about_product": "pTron Wireless Headphones in Grey. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Premium feel, sturdy build quality and excellent noise cancellation. | Amazing sound quality with deep bass, totally worth the money. | Very comfortable for long use and the battery life is great. | Sound is flat, not worth the price. | Poor build quality, broke within a month."
    },
    {
      "product_name": "Sony In-Ear Earphones - Blue Edition",
      "discounted_price": "7242",
      "actual_price": "8047",
      "discount_percentage": "10",
      "rating": "2.9",
      "rating_count": "4993",
      "about_product": "Sony In-Ear Earphones in Blue. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Very comfortable for long use and the battery life is great. | Premium feel, sturdy build quality and excellent noise cancellation. | Crystal clear audio, good for calls and music both. | Battery drains too quickly, very disappointing. | Connection keeps dropping, very frustrating."
    },
    {
      "product_name": "OnePlus Over-Ear Headphones - White Edition",
      "discounted_price": "4213",
      "actual_price": "7023",
      "discount_percentage": "40",
      "rating": "4.7",
      "rating_count": "999",
      "about_product": "OnePlus Over-Ear Headphones in White. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Very comfortable for long use and the battery life is great. | Crystal clear audio, good for calls and music both. | Premium feel, sturdy build quality and excellent noise cancellation. | Sound is flat, not worth the price. | Battery drains too quickly, very disappointing."
    },
    {
      "product_name": "Sony In-Ear Earphones - Blue Edition",
      "discounted_price": "14672",
      "actual_price": "18341",
      "discount_percentage": "20",
      "rating": "4.3",
      "rating_count": "1773",
      "about_product": "Sony In-Ear Earphones in Blue. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Very comfortable for long use and the battery life is great. | Premium feel, sturdy build quality and excellent noise cancellation. | Crystal clear audio, good for calls and music both. | Poor build quality, broke within a month. | Sound is flat, not worth the price."
    },
    {
      "product_name": "JBL Wireless Headphones - Red Edition",
      "discounted_price": "6711",
      "actual_price": "13423",
      "discount_percentage": "50",
      "rating": "2.5",
      "rating_count": "4897",
      "about_product": "JBL Wireless Headphones in Red. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Crystal clear audio, good for calls and music both. | Premium feel, sturdy build quality and excellent noise cancellation. | Amazing sound quality with deep bass, totally worth the money. | Battery drains too quickly, very disappointing. | Uncomfortable to wear for long periods of time."
    },
    {
      "product_name": "Skullcandy Truly Wireless Earbuds - Blue Edition",
      "discounted_price": "13405",
      "actual_price": "19151",
      "discount_percentage": "30",
      "rating": "4.6",
      "rating_count": "4603",
      "about_product": "Skullcandy Truly Wireless Earbuds in Blue. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Amazing sound quality with deep bass, totally worth the money. | Crystal clear audio, good for calls and music both. | Very comfortable for long use and the battery life is great. | Sound is flat, not worth the price. | Uncomfortable to wear for long periods of time."
    },
    {
      "product_name": "JBL In-Ear Earphones - White Edition",
      "discounted_price": "4083",
      "actual_price": "5833",
      "discount_percentage": "30",
      "rating": "3.5",
      "rating_count": "2195",
      "about_product": "JBL In-Ear Earphones in White. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Amazing sound quality with deep bass, totally worth the money. | Very comfortable for long use and the battery life is great. | Crystal clear audio, good for calls and music both. | Sound is flat, not worth the price. | Poor build quality, broke within a month."
    },
    {
      "product_name": "Boult Wireless Headphones - Green Edition",
      "discounted_price": "4763",
      "actual_price": "7939",
      "discount_percentage": "40",
      "rating": "2.8",
      "rating_count": "1472",
      "about_product": "Boult Wireless Headphones in Green. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Very comfortable for long use and the battery life is great. | Premium feel, sturdy build quality and excellent noise cancellation. | Amazing sound quality with deep bass, totally worth the money. | Battery drains too quickly, very disappointing. | Sound is flat, not worth the price."
    },
    {
      "product_name": "pTron Wired Earphones - Red Edition",
      "discounted_price": "676",
      "actual_price": "902",
      "discount_percentage": "25",
      "rating": "4.4",
      "rating_count": "2327",
      "about_product": "pTron Wired Earphones in Red. Great for music lovers, stylish and durable with high performance.",
      "reviews": "Crystal clear audio, good for calls and music both. | Very comfortable for long use and the battery life is great. | Premium feel, sturdy build quality and excellent noise cancellation. | Uncomfortable to wear for long periods of time. | Battery drains too quickly, very disappointing."
    }
  ]
}
"""

# Create the system prompt with the product data formatted in
FORMATTED_SYSTEM_PROMPT = """
You are an E-commerce Customer Support Virtual Agent for a headphones marketplace.  
You help customers with queries about headphones, using the provided PRODUCT_DATA JSON as your single source of truth.  
If a query goes beyond the PRODUCT_DATA or your scope, you politely hand over to a Live Agent.  

Context: {0}

You have access to a structured JSON object stored in a variable called PRODUCT_DATA.  
This JSON contains an array of products with the following fields:  

- product_name → The brand and model name of the headphone.  
- discounted_price → Final selling price after applying deals/offers (in INR).  
- actual_price → Original listed price (in INR).  
- discount_percentage → Percentage discount from actual price to discounted price.  
- rating → Average customer rating (1–5).  
- rating_count → Number of customers who rated the product.  
- about_product → A short 3–4 line description of the product (features, type, color, etc.).  
- reviews → 5 detailed customer reviews with a mix of positive and negative experiences.  

Agent Behavior Guidelines  

Tone & Style  
- Be polite, concise, and helpful.  
- Use natural conversational flow like a customer service agent.  

Query Handling  
- Product Info Queries: Provide details (price, rating, description, reviews, etc.) from PRODUCT_DATA.  
- Comparisons: Highlight differences (price, features, ratings, reviews) across products.  
- Filtering/Sorting: Apply filters (brand, price range, rating, type) or sort results (lowest price, highest rating, etc.).  
- Deals & Offers: Share discounted price, original price, and discount percentage.  
- Reviews: Summarize reviews or provide individual reviews on request.  
- Recommendations: Suggest alternatives based on budget, need (e.g., gaming, travel, wireless, etc.), or rating.  

Order Related Queries (like tracking, returns, complaints):  
- Provide a simulated conversational flow and then hand off to a live agent.  

Live Agent Handover  
- If a query cannot be resolved using PRODUCT_DATA or standard FAQ (e.g., real-time delivery status, warranty claims, refund escalation), respond:  
  "I'll connect you with a live agent who can help further with this request."  

Boundaries  
- Do not make up new product data outside PRODUCT_DATA.  
- Always base your answers only on PRODUCT_DATA.  
""".format(PRODUCT_DATA)

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

def get_llm_response(messages, provider="openai"):
    """
    Get response from a language model
    """
    if provider == "openai":
        try:
            # Try to get from Streamlit secrets
            api_key = st.secrets["OPENAI_API_KEY"]
        except:
            # Fallback - hardcoded key for testing
            api_key = "no key"
        
        try:
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3,
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error communicating with OpenAI: {str(e)}"

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
    
    # Initialize messages list with system prompt that already includes the product data
    messages = [
        {"role": "system", "content": FORMATTED_SYSTEM_PROMPT}
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
st.title("Headphones Marketplace Support")
st.markdown("Welcome to our headphone marketplace support! How can I help you today?")

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

# Update sidebar with more product-specific examples
st.sidebar.title("Example Queries")
st.sidebar.markdown("""
### Product Related:
- What are the best headphones under ₹5000?
- Compare Sony and JBL earphones
- Show me wireless earbuds with good battery life
- Which headphones have the highest rating?
- Tell me about pTron earphones reviews
- What's the most discounted headphone available?
- I need headphones for gaming

### Order Related:
- What's the status of order #123?
- I want to return my order #456
- What's your shipping policy?
- How do I track my order?
""")

# About section
st.sidebar.title("About")
st.sidebar.info("This is a demo customer support chatbot for a headphones marketplace that can help with product information and basic order tracking.")

# Display product count in sidebar
st.sidebar.title("Product Database Stats")
st.sidebar.write("Products: 10")
st.sidebar.write("Brands: pTron, Sony, OnePlus, JBL, Skullcandy, Boult")