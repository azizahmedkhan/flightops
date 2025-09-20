import httpx
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

def generate_natural_language_response(
    customer_message: str,
    sentiment_response: Dict[str, Any],
    flight_data: Optional[Dict[str, Any]] = None,
    policy_data: Optional[List[Dict[str, Any]]] = None,
    session_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a natural, user-friendly response based on customer inquiry,
    sentiment analysis, and available data. Now uses the LLM-generated response
    as the base and enhances it with additional data.
    """
    
    # Extract the LLM-generated response and analysis
    llm_response = sentiment_response.get("response_to_customer", "")
    analysis = sentiment_response.get("analysis", {})
    
    # If we have a good LLM response, use it as the base
    if llm_response and len(llm_response.strip()) > 10:
        base_response = llm_response
    else:
        # Fallback to our custom generation if LLM response is poor
        base_response = generate_fallback_response(customer_message, analysis, session_context)
    
    # Enhance the response with additional data if available
    enhanced_response = enhance_response_with_data(
        base_response, customer_message, flight_data, policy_data, session_context
    )
    
    return enhanced_response

def generate_fallback_response(
    customer_message: str,
    analysis: Dict[str, Any],
    session_context: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a fallback response when LLM response is not available."""
    
    # Extract key information
    sentiment = analysis.get("sentiment", "neutral")
    urgency = analysis.get("urgency_level", "low")
    customer_name = session_context.get("customer_name", "there") if session_context else "there"
    flight_no = session_context.get("flight_no", "your flight") if session_context else "your flight"
    
    # Start with appropriate greeting based on sentiment
    if sentiment == "negative" and urgency == "high":
        greeting = f"I'm really sorry to hear about your concerns, {customer_name}. I understand this is frustrating and I'm here to help resolve this right away."
    elif sentiment == "negative":
        greeting = f"I apologize for any inconvenience, {customer_name}. Let me help you with that."
    elif sentiment == "positive":
        greeting = f"Thank you for reaching out, {customer_name}! I'm happy to help you."
    else:
        greeting = f"Hello {customer_name}, I'm here to help you with your inquiry about {flight_no}."
    
    # Analyze the customer's question to determine what they're asking
    question_type = analyze_question_type(customer_message)
    
    # Generate response based on question type
    response_parts = [greeting]
    
    if question_type == "flight_status":
        response_parts.append("Let me check the current status of your flight for you.")
    elif question_type == "airport_timing":
        response_parts.append("I can help you with airport timing information.")
    elif question_type == "policy_question":
        response_parts.append("I'd be happy to help you with policy questions.")
    elif question_type == "crew_inquiry":
        response_parts.append("I can provide you with crew information.")
    elif question_type == "aircraft_inquiry":
        response_parts.append("I can help you with aircraft details.")
    else:
        response_parts.append("I'm here to help you with your flight-related questions.")
    
    # Add appropriate closing based on sentiment and urgency
    if urgency == "high":
        response_parts.append("I'm escalating this to our senior support team for immediate attention.")
    elif sentiment == "negative":
        response_parts.append("I sincerely apologize for any inconvenience caused. Is there anything else I can help you with?")
    else:
        response_parts.append("Is there anything else I can help you with regarding your flight?")
    
    return " ".join(response_parts)

def enhance_response_with_data(
    base_response: str,
    customer_message: str,
    flight_data: Optional[Dict[str, Any]] = None,
    policy_data: Optional[List[Dict[str, Any]]] = None,
    session_context: Optional[Dict[str, Any]] = None
) -> str:
    """Enhance the base response with additional flight and policy data."""
    
    # If we don't have additional data, return the base response
    if not flight_data and not policy_data:
        return base_response
    
    response_parts = [base_response]
    
    # Add flight-specific information if available
    if flight_data:
        flight_info = generate_flight_info_addition(flight_data, customer_message)
        if flight_info:
            response_parts.append(flight_info)
    
    # Add policy information if available and relevant
    if policy_data and any(word in customer_message.lower() for word in ["policy", "compensation", "refund", "rights"]):
        policy_info = generate_policy_info_addition(policy_data)
        if policy_info:
            response_parts.append(policy_info)
    
    return " ".join(response_parts)

def generate_flight_info_addition(flight_data: Dict[str, Any], customer_message: str) -> str:
    """Generate additional flight information to append to the response."""
    message_lower = customer_message.lower()
    
    if "on time" in message_lower or "delayed" in message_lower or "status" in message_lower:
        status = flight_data.get("status", "Unknown")
        departure_time = flight_data.get("scheduled_departure", "TBD")
        arrival_time = flight_data.get("scheduled_arrival", "TBD")
        
        if status.lower() == "on time":
            return f"Your flight is currently on time, scheduled to depart at {departure_time} and arrive at {arrival_time}."
        elif status.lower() == "delayed":
            delay_minutes = flight_data.get("delay_minutes", 0)
            return f"Your flight is experiencing a delay of approximately {delay_minutes} minutes. The new departure time is estimated to be {departure_time}."
        else:
            return f"Your flight status is {status}, with departure at {departure_time} and arrival at {arrival_time}."
    
    elif "airport" in message_lower or "reach" in message_lower or "arrive" in message_lower:
        flight_type = flight_data.get("flight_type", "domestic")
        if flight_type.lower() == "international":
            return "For your international flight, I recommend arriving at the airport at least 3 hours before departure."
        else:
            return "For your domestic flight, I recommend arriving at the airport at least 2 hours before departure."
    
    return ""

def generate_policy_info_addition(policy_data: List[Dict[str, Any]]) -> str:
    """Generate additional policy information to append to the response."""
    if not policy_data:
        return ""
    
    # Extract key policy information
    policy_summary = []
    for policy in policy_data[:1]:  # Limit to top policy
        title = policy.get("title", "Policy")
        snippet = policy.get("snippet", "")
        if snippet:
            policy_summary.append(f"According to our {title}: {snippet[:150]}...")
    
    if policy_summary:
        return f" {policy_summary[0]}"
    
    return ""

def analyze_question_type(message: str) -> str:
    """Analyze the customer message to determine what type of information they're seeking."""
    message_lower = message.lower()
    
    # Flight status keywords
    if any(word in message_lower for word in ["on time", "delayed", "cancelled", "status", "departure", "arrival"]):
        return "flight_status"
    
    # Airport timing keywords
    if any(word in message_lower for word in ["airport", "reach", "arrive", "check-in", "boarding", "time"]):
        return "airport_timing"
    
    # Policy keywords
    if any(word in message_lower for word in ["policy", "compensation", "refund", "rebook", "rights", "entitled"]):
        return "policy_question"
    
    # Crew keywords
    if any(word in message_lower for word in ["crew", "pilot", "captain", "flight attendant", "staff"]):
        return "crew_inquiry"
    
    # Aircraft keywords
    if any(word in message_lower for word in ["aircraft", "plane", "airbus", "boeing", "aircraft type"]):
        return "aircraft_inquiry"
    
    return "general"

def generate_flight_status_response(flight_data: Optional[Dict[str, Any]], customer_message: str) -> str:
    """Generate response for flight status inquiries."""
    if not flight_data:
        return "I don't have current flight information available right now. Let me check our systems for you."
    
    flight_no = flight_data.get("flight_no", "your flight")
    status = flight_data.get("status", "Unknown")
    departure_time = flight_data.get("scheduled_departure", "TBD")
    arrival_time = flight_data.get("scheduled_arrival", "TBD")
    
    if status.lower() == "on time":
        return f"Great news! {flight_no} is currently on time. It's scheduled to depart at {departure_time} and arrive at {arrival_time}."
    elif status.lower() == "delayed":
        delay_minutes = flight_data.get("delay_minutes", 0)
        return f"I can see that {flight_no} is experiencing a delay of approximately {delay_minutes} minutes. The new departure time is estimated to be {departure_time}."
    elif status.lower() == "cancelled":
        return f"I'm sorry to inform you that {flight_no} has been cancelled. We're working on rebooking options for all affected passengers."
    else:
        return f"Your flight {flight_no} is currently showing as {status}. The scheduled departure is {departure_time} and arrival is {arrival_time}."

def generate_airport_timing_response(flight_data: Optional[Dict[str, Any]], customer_message: str) -> str:
    """Generate response for airport timing inquiries."""
    if not flight_data:
        return "For airport timing, I recommend arriving at least 2 hours before domestic flights and 3 hours before international flights."
    
    flight_type = flight_data.get("flight_type", "domestic")
    departure_time = flight_data.get("scheduled_departure", "")
    
    if flight_type.lower() == "international":
        return f"For your international flight, I recommend arriving at the airport at least 3 hours before departure. Check-in typically closes 60 minutes before departure, and boarding begins 45 minutes before departure."
    else:
        return f"For your domestic flight, I recommend arriving at the airport at least 2 hours before departure. Check-in typically closes 30 minutes before departure, and boarding begins 30 minutes before departure."

def generate_policy_response(policy_data: Optional[List[Dict[str, Any]]], customer_message: str) -> str:
    """Generate response for policy and procedure inquiries."""
    if not policy_data:
        return "I'd be happy to help you with policy questions. Let me look up the relevant information for you."
    
    # Extract key policy information
    policy_summary = []
    for policy in policy_data[:2]:  # Limit to top 2 policies
        title = policy.get("title", "Policy")
        snippet = policy.get("snippet", "")
        if snippet:
            policy_summary.append(f"According to our {title}: {snippet[:200]}...")
    
    if policy_summary:
        return " ".join(policy_summary)
    else:
        return "Based on our policies, I can help you with rebooking, compensation, or other service-related questions. What specific policy information are you looking for?"

def generate_crew_response(flight_data: Optional[Dict[str, Any]], customer_message: str) -> str:
    """Generate response for crew-related inquiries."""
    if not flight_data or "crew_details" not in flight_data:
        return "I can help you with crew information. Let me check the details for your flight."
    
    crew_details = flight_data.get("crew_details", {})
    captain = crew_details.get("captain", {})
    first_officer = crew_details.get("first_officer", {})
    
    response = "Here's the crew information for your flight:"
    
    if captain:
        response += f" Captain: {captain.get('name', 'Name not available')} with {captain.get('experience_years', 'N/A')} years of experience."
    
    if first_officer:
        response += f" First Officer: {first_officer.get('name', 'Name not available')} with {first_officer.get('experience_years', 'N/A')} years of experience."
    
    return response

def generate_aircraft_response(flight_data: Optional[Dict[str, Any]], customer_message: str) -> str:
    """Generate response for aircraft-related inquiries."""
    if not flight_data or "aircraft" not in flight_data:
        return "I can help you with aircraft information. Let me check the details for your flight."
    
    aircraft = flight_data.get("aircraft", {})
    aircraft_type = aircraft.get("type", "Unknown")
    registration = aircraft.get("registration", "Unknown")
    capacity = aircraft.get("capacity", "Unknown")
    
    return f"Your flight is operated by a {aircraft_type} aircraft (Registration: {registration}) with a capacity of {capacity} passengers."

def generate_general_response(customer_message: str, flight_data: Optional[Dict[str, Any]]) -> str:
    """Generate a general response for unclear inquiries."""
    return "I understand you have a question about your flight. I'm here to help with flight status, rebooking options, policies, or any other flight-related inquiries. Could you please let me know what specific information you need?"

def lookup_flight_data(flight_no: str, date: str, agent_url: str) -> Optional[Dict[str, Any]]:
    """Look up flight data from the agent service."""
    try:
        response = httpx.post(
            f"{agent_url}/analyze-disruption",
            json={
                "question": f"Get flight details for {flight_no} on {date}",
                "flight_no": flight_no,
                "date": date
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("tools_payload", {}).get("flight", {})
    except Exception as e:
        print(f"Error looking up flight data: {e}")
    
    return None

def lookup_policy_data(question: str, retrieval_url: str) -> Optional[List[Dict[str, Any]]]:
    """Look up policy data from the retrieval service."""
    try:
        response = httpx.post(
            f"{retrieval_url}/search",
            json={
                "q": question + " policy compensation rebooking",
                "k": 3
            },
            timeout=15.0
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
    except Exception as e:
        print(f"Error looking up policy data: {e}")
    
    return None

def enhance_sentiment_analysis_with_context(
    sentiment_analysis: Dict[str, Any],
    customer_message: str,
    session_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Enhance sentiment analysis with additional context and insights."""
    
    # Add contextual insights
    enhanced = sentiment_analysis.copy()
    
    # Add customer name if available
    if session_context and "customer_name" in session_context:
        enhanced["customer_name"] = session_context["customer_name"]
    
    # Add flight context
    if session_context and "flight_no" in session_context:
        enhanced["flight_context"] = f"Flight {session_context['flight_no']}"
    
    # Add message analysis
    enhanced["message_length"] = len(customer_message)
    enhanced["contains_question"] = "?" in customer_message
    enhanced["contains_urgency_words"] = any(word in customer_message.lower() 
                                           for word in ["urgent", "immediately", "asap", "emergency"])
    
    # Add recommended actions
    urgency = enhanced.get("urgency_level", "low")
    sentiment = enhanced.get("sentiment", "neutral")
    
    if urgency == "high":
        enhanced["recommended_actions"] = ["escalate_to_senior_support", "provide_immediate_response", "follow_up_within_30_minutes"]
    elif sentiment == "negative":
        enhanced["recommended_actions"] = ["acknowledge_concerns", "provide_empathetic_response", "offer_solutions"]
    else:
        enhanced["recommended_actions"] = ["provide_helpful_information", "maintain_positive_tone"]
    
    return enhanced
