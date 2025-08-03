import os
import requests
from serpapi import GoogleSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

def search_flights(origin, destination, departure_date, return_date=None, adults=1, travel_class="Economy"):
    """
    Search for flights using SerpAPI Google Flights
    
    Args:
        origin (str): Origin airport code (e.g., "JFK")
        destination (str): Destination airport code (e.g., "LAX")
        departure_date (str): Departure date in YYYY-MM-DD format
        return_date (str, optional): Return date in YYYY-MM-DD format for round trip
        adults (int): Number of adult passengers
        travel_class (str): Travel class (Economy, Premium Economy, Business, First)
    
    Returns:
        dict: Flight search results or error info
    """
    try:
        print(f"🛫 Searching flights: {origin} → {destination}, Departure: {departure_date}, Return: {return_date}")
        
        # Map travel class to SerpAPI format
        class_mapping = {
            "economy": "1",
            "premium economy": "2", 
            "business": "3",
            "first": "4"
        }
        
        # Get the correct travel class code
        travel_class_code = class_mapping.get(travel_class.lower(), "1")  # Default to Economy
        print(f"🎫 Travel class: {travel_class} → Code: {travel_class_code}")
        
        # Build search parameters
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "adults": adults,
            "travel_class": travel_class_code,
            "currency": "USD",
            "hl": "en",
            "api_key": SERPAPI_API_KEY
        }
        
        # Add return date for round trip - FIXED THE BUG HERE
        if return_date:
            params["return_date"] = return_date
            params["type"] = "1"  # FIXED: Round trip should be "1", not "2"
        else:
            params["type"] = "2"  # FIXED: One way should be "2", not "1"
        
        search = GoogleSearch(params)
        result = search.get_dict()
        
        if "error" in result:
            print(f"❌ SerpAPI Error: {result['error']}")
            return {"error": result["error"]}
        
        # Print raw result for debugging
        print("🔍 Raw SerpAPI response keys:", list(result.keys()))
        
        # Extract and format flight data
        flights_data = {
            "search_info": {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "adults": adults,
                "travel_class": travel_class
            },
            "best_flights": [],
            "other_flights": [],
            "search_metadata": result.get("search_metadata", {})
        }
        
        # Process best flights
        if "best_flights" in result:
            print(f"📊 Found {len(result['best_flights'])} best flights")
            for flight_option in result["best_flights"]:
                formatted_flight = format_flight_data(flight_option)
                if formatted_flight:
                    flights_data["best_flights"].append(formatted_flight)
        
        # Process other flights
        if "other_flights" in result:
            print(f"📊 Found {len(result['other_flights'])} other flights")
            for flight_option in result["other_flights"][:10]:  # Limit to 10 other flights
                formatted_flight = format_flight_data(flight_option)
                if formatted_flight:
                    flights_data["other_flights"].append(formatted_flight)
        
        print(f"✅ Successfully formatted {len(flights_data['best_flights'])} best flights and {len(flights_data['other_flights'])} other options")
        return flights_data
        
    except Exception as e:
        print(f"❌ Flight search error: {e}")
        return {"error": str(e)}

def format_flight_data(flight_option):
    """
    Format individual flight data from SerpAPI response
    
    Args:
        flight_option (dict): Raw flight option from SerpAPI
    
    Returns:
        dict: Formatted flight data
    """
    try:
        flights = flight_option.get("flights", [])
        if not flights:
            print("⚠️ No flights in flight option")
            return None
        
        # Extract basic info
        total_duration = flight_option.get("total_duration", "N/A")
        price = flight_option.get("price", "N/A")
        carbon_emissions = flight_option.get("carbon_emissions", {})
        
        # Format flight segments
        segments = []
        for flight in flights:
            segment = {
                "airline": flight.get("airline", "Unknown"),
                "airline_logo": flight.get("airline_logo", ""),
                "flight_number": flight.get("flight_number", "N/A"),
                "departure_airport": {
                    "name": flight.get("departure_airport", {}).get("name", "N/A"),
                    "id": flight.get("departure_airport", {}).get("id", "N/A"),
                    "time": flight.get("departure_airport", {}).get("time", "N/A")
                },
                "arrival_airport": {
                    "name": flight.get("arrival_airport", {}).get("name", "N/A"),
                    "id": flight.get("arrival_airport", {}).get("id", "N/A"),
                    "time": flight.get("arrival_airport", {}).get("time", "N/A")
                },
                "duration": flight.get("duration", "N/A"),
                "airplane": flight.get("airplane", "N/A"),
                "travel_class": flight.get("travel_class", "N/A")
            }
            segments.append(segment)
        
        return {
            "price": price,
            "total_duration": total_duration,
            "carbon_emissions": {
                "this_flight": carbon_emissions.get("this_flight", "N/A"),
                "typical_for_this_route": carbon_emissions.get("typical_for_this_route", "N/A"),
                "difference_percent": carbon_emissions.get("difference_percent", "N/A")
            },
            "segments": segments,
            "layovers": flight_option.get("layovers", []),
            "booking_token": flight_option.get("booking_token", ""),
            "extensions": flight_option.get("extensions", [])
        }
        
    except Exception as e:
        print(f"❌ Error formatting flight data: {e}")
        return None

def format_flights_response(flights_data):
    """
    Format flight search results for AI consumption
    
    Args:
        flights_data (dict): Formatted flight search results
    
    Returns:
        str: Formatted flight results for AI
    """
    if "error" in flights_data:
        return f"FLIGHT_SEARCH_ERROR: {flights_data['error']}"
    
    search_info = flights_data.get("search_info", {})
    best_flights = flights_data.get("best_flights", [])
    other_flights = flights_data.get("other_flights", [])
    
    formatted_response = "FLIGHT_SEARCH_RESULTS:\n\n"
    formatted_response += f"**SEARCH DETAILS:**\n"
    formatted_response += f"Route: {search_info.get('origin')} → {search_info.get('destination')}\n"
    formatted_response += f"Departure: {search_info.get('departure_date')}\n"
    
    if search_info.get('return_date'):
        formatted_response += f"Return: {search_info.get('return_date')}\n"
        formatted_response += f"Trip Type: Round Trip\n"
    else:
        formatted_response += f"Trip Type: One Way\n"
    
    formatted_response += f"Passengers: {search_info.get('adults')} adult(s)\n"
    formatted_response += f"Class: {search_info.get('travel_class')}\n\n"
    
    # Best flights
    if best_flights:
        formatted_response += f"**BEST FLIGHT OPTIONS ({len(best_flights)} found):**\n\n"
        for i, flight in enumerate(best_flights, 1):
            formatted_response += format_single_flight_for_ai(flight, i)
    
    # Other flights (limit to 5 for brevity)
    if other_flights:
        formatted_response += f"\n**OTHER FLIGHT OPTIONS (showing first 5 of {len(other_flights)}):**\n\n"
        for i, flight in enumerate(other_flights[:5], len(best_flights) + 1):
            formatted_response += format_single_flight_for_ai(flight, i)
    
    if not best_flights and not other_flights:
        formatted_response += "**NO FLIGHTS FOUND**\n"
        formatted_response += "No flights were found for the specified route and dates. Please try different dates or airports.\n"
    
    formatted_response += "\n**INSTRUCTION FOR AI:** Use only the flight information provided above. Include prices, airlines, times, and duration. Format this information in a user-friendly way with clear pricing and timing details."
    
    return formatted_response

def format_single_flight_for_ai(flight, index):
    """Format a single flight for AI consumption"""
    segments = flight.get("segments", [])
    price = flight.get("price", "N/A")
    duration = flight.get("total_duration", "N/A")
    carbon = flight.get("carbon_emissions", {}).get("this_flight", "N/A")
    layovers = flight.get("layovers", [])
    
    flight_text = f"**{index}. FLIGHT OPTION - {price}**\n"
    flight_text += f"   Total Duration: {duration}\n"
    
    if carbon != "N/A":
        flight_text += f"   Carbon Emissions: {carbon}\n"
    
    if layovers:
        layover_info = ", ".join([f"{layover.get('duration', 'N/A')} in {layover.get('name', 'Unknown')}" for layover in layovers])
        flight_text += f"   Layovers: {layover_info}\n"
    else:
        flight_text += f"   Direct Flight: Yes\n"
    
    for j, segment in enumerate(segments, 1):
        airline = segment.get("airline", "Unknown")
        flight_num = segment.get("flight_number", "N/A")
        dep_airport = segment.get("departure_airport", {})
        arr_airport = segment.get("arrival_airport", {})
        seg_duration = segment.get("duration", "N/A")
        airplane = segment.get("airplane", "N/A")
        
        if len(segments) > 1:
            flight_text += f"\n   === SEGMENT {j} ===\n"
        
        flight_text += f"   Airline: {airline} {flight_num}\n"
        flight_text += f"   Aircraft: {airplane}\n"
        flight_text += f"   Departure: {dep_airport.get('name', 'N/A')} ({dep_airport.get('id', 'N/A')}) at {dep_airport.get('time', 'N/A')}\n"
        flight_text += f"   Arrival: {arr_airport.get('name', 'N/A')} ({arr_airport.get('id', 'N/A')}) at {arr_airport.get('time', 'N/A')}\n"
        flight_text += f"   Flight Duration: {seg_duration}\n"
    
    flight_text += "\n"
    return flight_text

def format_flights_for_user(flights_data):
    """
    Format flights data for direct user display (used in travel summary)
    
    Args:
        flights_data (dict): Formatted flight search results
    
    Returns:
        str: User-friendly formatted flights section
    """
    if "error" in flights_data:
        return f"\n\n✈️ **Flight Search Error:** {flights_data['error']}"
    
    search_info = flights_data.get("search_info", {})
    best_flights = flights_data.get("best_flights", [])
    
    if not best_flights:
        return f"\n\n✈️ **Flight Search:** No flights found for {search_info.get('origin')} → {search_info.get('destination')}"
    
    flights_section = f"\n\n✈️ **Flight Options for {search_info.get('origin')} → {search_info.get('destination')}:**\n"
    
    # Show top 3 flight options
    for i, flight in enumerate(best_flights[:3], 1):
        price = flight.get("price", "N/A")
        duration = flight.get("total_duration", "N/A")
        segments = flight.get("segments", [])
        
        flights_section += f"\n**Option {i}: {price}** (Duration: {duration})\n"
        
        if segments:
            first_segment = segments[0]
            last_segment = segments[-1] if len(segments) > 1 else first_segment
            
            dep_time = first_segment.get("departure_airport", {}).get("time", "N/A")
            arr_time = last_segment.get("arrival_airport", {}).get("time", "N/A")
            airline = first_segment.get("airline", "Unknown")
            
            flights_section += f"📅 {dep_time} → {arr_time} ({airline}"
            
            if len(segments) > 1:
                flights_section += f" + {len(segments) - 1} stop(s)"
            
            flights_section += ")\n"
    
    if len(best_flights) > 3:
        flights_section += f"\n... and {len(best_flights) - 3} more options available\n"
    
    return flights_section

def validate_serpapi():
    """
    Validate that SerpAPI key is available
    
    Returns:
        bool: True if API key is available, False otherwise
    """
    if not SERPAPI_API_KEY:
        print("⚠️ Warning: SERPAPI_API_KEY not found in environment variables")
        return False
    
    print("✅ SerpAPI key found")
    return True

def print_flights_to_terminal(flights_data):
    """
    Print flight search results to terminal in a nice format
    
    Args:
        flights_data (dict): Formatted flight search results
    """
    print("\n" + "="*80)
    print(f"🛫 FLIGHT SEARCH RESULTS")
    print("="*80)
    
    if "error" in flights_data:
        print(f"❌ Error: {flights_data['error']}")
        print("="*80 + "\n")
        return
    
    search_info = flights_data.get("search_info", {})
    print(f"Route: {search_info.get('origin')} → {search_info.get('destination')}")
    print(f"Departure: {search_info.get('departure_date')}")
    if search_info.get('return_date'):
        print(f"Return: {search_info.get('return_date')}")
    print(f"Passengers: {search_info.get('adults')} adult(s)")
    print(f"Class: {search_info.get('travel_class')}")
    
    best_flights = flights_data.get("best_flights", [])
    other_flights = flights_data.get("other_flights", [])
    
    if best_flights:
        print(f"\n🌟 BEST FLIGHTS ({len(best_flights)}):")
        print("-" * 40)
        for i, flight in enumerate(best_flights, 1):
            print_single_flight_to_terminal(flight, i)
    
    if other_flights:
        print(f"\n✈️ OTHER OPTIONS (showing first 3 of {len(other_flights)}):")
        print("-" * 40)
        for i, flight in enumerate(other_flights[:3], len(best_flights) + 1):
            print_single_flight_to_terminal(flight, i)
    
    print("\n" + "="*80 + "\n")

def print_single_flight_to_terminal(flight, index):
    """Print a single flight to terminal"""
    price = flight.get("price", "N/A")
    duration = flight.get("total_duration", "N/A")
    segments = flight.get("segments", [])
    
    print(f"\n{index}. {price} - {duration}")
    
    for j, segment in enumerate(segments, 1):
        airline = segment.get("airline", "Unknown")
        flight_num = segment.get("flight_number", "N/A")
        dep_airport = segment.get("departure_airport", {})
        arr_airport = segment.get("arrival_airport", {})
        
        dep_time = dep_airport.get("time", "N/A")
        arr_time = arr_airport.get("time", "N/A")
        dep_code = dep_airport.get("id", "N/A")
        arr_code = arr_airport.get("id", "N/A")
        
        if len(segments) > 1:
            print(f"   Segment {j}: {airline} {flight_num}")
        else:
            print(f"   {airline} {flight_num}")
        
        print(f"   {dep_time} {dep_code} → {arr_time} {arr_code}")