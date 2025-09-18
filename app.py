import streamlit as st
import openai
import csv
from datetime import datetime, timedelta
import os
from collections import defaultdict

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "failed_attempts" not in st.session_state:
    st.session_state.failed_attempts = 0

# Load the Amazon product dataset using CSV
@st.cache_data
def load_product_data():
    """Load and cache the Amazon product dataset"""
    try:
        products = []
        with open('amazon_products.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                products.append(row)
        return products
    except Exception as e:
        st.error(f"Error loading product data: {e}")
        return []  # Return empty list on error

# Initialize product data in session state
if "product_data" not in st.session_state:
    st.session_state.product_data = load_product_data()

# Mock order database (keeping original functionality)
ORDERS = {
    "123": {"status": "shipped", "eta": (datetime.now() + timedelta(days=3)).strftime("%B %d"), "items": ["Wireless Earbuds", "Phone Case"]},
    "456": {"status": "delivered", "delivery_date": "September 15", "items": ["Smart Watch", "Charging Cable"]},
    "789": {"status": "processing", "ship_date": (datetime.now() + timedelta(days=2)).strftime("%B %d"), "items": ["Bluetooth Speaker"]}
}

# Escalation triggers
ESCALATION_KEYWORDS = ["fraud", "dispute", "human", "agent", "supervisor", "manager", "speak to someone", "real person"]

# Updated system prompt that combines order support and product information
SYSTEM_PROMPT = """
You are a helpful, professional customer support agent for "ShopEasy", an e-commerce platform. 
Your role is to assist customers with their inquiries about orders, returns, shipping, and products.

Your tone should be:
- Professional but warm
- Concise but thorough
- Helpful without overpromising

You can assist with TWO main types of queries:

1. ORDER MANAGEMENT:
   - If they ask about order status, you can check orders #123 (shipped, arriving in 3 days), #456 (delivered Sept 15), or #789 (processing, ships in 2 days). For other order numbers, apologize and offer to escalate.
   - For returns/refunds, collect the order number and reason, then confirm the return has been initiated.
   - For shipping policy questions, explain that standard shipping is 3-5 business days and express is 1-2 business days.

2. PRODUCT INFORMATION:
   - You have access to a database of Amazon products with details like name, category, pricing, ratings, and reviews.
   - When customers ask about products, reference specific details from this database.
   - For product recommendations, use actual ratings, prices, and categories from the database.
   - Summarize review content when customers ask about specific products.

IMPORTANT ESCALATION RULES:
- Escalate immediately if the customer mentions fraud, payment disputes, or specifically requests a human agent.
- After 2 failed attempts to understand the customer's request, offer to escalate to a human agent.
- When escalating, say: "I'll connect you with a human support agent who can better assist you with this. Please hold while I transfer your chat."

Remember to be solution-oriented and thank the customer for their patience.
"""

def search_products(query, products, limit=5):
    """
    Search for products in the dataset based on query
    Returns relevant product information
    """
    if not products:
        return []
        
    # Convert query to lowercase for case-insensitive search
    query_lower = query.lower()
    
    # Create a combined relevance score based on different fields
    results = []
    
    for product in products:
        relevance = 0
        
        # Check product name
        if product.get('Product Name') and query_lower in product.get('Product Name', '').lower():
            relevance += 10
        
        # Check category
        #if product.get('category') and query_lower in product.get('category', '').lower():
            #relevance += 5
        
        # Check product description
        if product.get('About Product') and query_lower in product.get('About Product', '').lower():
            relevance += 3
            
        # Check review content
        if product.get('Reviews') and query_lower in product.get('Reviews', '').lower():
            relevance += 2
        
        # If there's any relevance, add to results
        if relevance > 0:
            product_copy = product.copy()
            product_copy['relevance'] = relevance
            results.append(product_copy)
    
    # Sort by relevance and limit results
    results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
    return results[:limit]

def get_product_context(query, products):
    """
    Generate context about products based on the user query
    to provide to the LLM
    """
    if not products:
        return "Product database is not available."
        
    # Search for relevant products
    relevant_products = search_products(query, products)
    
    if not relevant_products:
        return "No products found matching the query."
    
    # Format the product information as context
    context = "Here are details about relevant products in our database:\n\n"
    
    for i, product in enumerate(relevant_products, 1):
        context += f"Product {i}:\n"
        context += f"Name: {product.get('Product Name', 'N/A')}\n"
        #context += f"Category: {product.get('category', 'N/A')}\n"
        context += f"Pricing: ₹{product.get('Discounted Price', 'N/A')} (Original: ₹{product.get('Actual Price', 'N/A')}, Discount: {product.get('Discount Percentage', 'N/A')}%)\n"
        context += f"Rating: {product.get('Rating', 'N/A')}/5 based on {product.get('Rating Count', 'N/A')} Reviews\n"
        context += f"Description: {product.get('About Product', 'N/A')}\n"
        context += f"Review: {product.get('Reviews', 'N/A')}\n\n"
    
    return context

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

def is_product_query(user_message):
    """Determine if a message is likely a product-related query"""
    product_keywords = [
        "product", "item", "buy", "purchase", "price", "cost", "review", 
        "rating", "recommend", "comparison", "compare", "difference", "quality",
        "headphone", "earphone", "earbud", "watch", "mobile", "phone", "laptop",
        "best", "top", "affordable", "cheap", "expensive", "worth", "alternative"
    ]
    
    return any(keyword in user_message.lower() for keyword in product_keywords)

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
    
    # Initialize messages list with system prompt
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # If it's a product query, add product context
    if is_product_query(user_message) and st.session_state.product_data:
        product_context = get_product_context(user_message, st.session_state.product_data)
        messages.append({"role": "system", "content": f"Product Database Information:\n{product_context}"})
    
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

# Update sidebar with both order and product examples
st.sidebar.title("Example Queries")
st.sidebar.markdown("""
### Order Related:
- What's the status of order #123?
- I want to return my order #456
- What's your shipping policy?
- How do I track my order?

### Product Related:
- What are the best headphones under ₹5000?
- Can you recommend a good smartwatch?
- Compare wireless earbuds in your store
- Show me products with high ratings
- What do reviews say about noise cancellation headphones?
""")

# About section
st.sidebar.title("About")
st.sidebar.info("This is a demo customer support chatbot for ShopEasy e-commerce platform that can help with both order tracking and product information.")

# Display dataset stats in sidebar if data is loaded
if st.session_state.product_data:
    st.sidebar.title("Product Database Stats")
    
    # Count unique product IDs and categories
    product_ids = set()
    categories = set()
    
    for product in st.session_state.product_data:
        if product.get('product_id'):
            product_ids.add(product.get('product_id'))
        if product.get('category'):
            categories.add(product.get('category'))
    
    st.sidebar.write(f"Products: {len(product_ids)}")

    st.sidebar.write(f"Categories: {len(categories)}")
