import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from ai_utils import ask_ai_with_history

# Import Tavily utilities
try:
    from tavily_utils import search_activities, format_activities_response, format_activities_for_user, validate_tavily_api
except ImportError:
    # Fallback import if there are path issues
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from tavily_utils import search_activities, format_activities_response, format_activities_for_user, validate_tavily_api

# Import Flight utilities
try:
    from serpapi_utils import (
        search_flights, format_flights_response, 
        format_flights_for_user, validate_serpapi,
        print_flights_to_terminal
    )
except ImportError:
    # Fallback import if there are path issues
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from serpapi_utils import (
        search_flights, format_flights_response, 
        format_flights_for_user, validate_serpapi,
        print_flights_to_terminal
    )

# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chat history with improved system message
chat_history = [
    {
        "role": "system", 
        "content": (
            "You are TripAI, a smart AI travel assistant. Your job is to collect travel information from users step by step and return it in JSON format when complete, AND to help with activity recommendations and flight searches.\n\n"
            
            "ACTIVITY SEARCH CAPABILITY:\n"
            "When a user asks about activities, attractions, things to do, or travel recommendations for a specific place, you should request a search by responding with:\n"
            "SEARCH_ACTIVITIES: [location] | [user_query]\n"
            "Where [location] is the destination they're asking about and [user_query] is their original question.\n"
            "For example:\n"
            "- User: 'What are the best things to do in Paris?'\n"
            "- Your response: 'SEARCH_ACTIVITIES: Paris | What are the best things to do in Paris?'\n"
            "- User: 'I want activities in Tokyo for families'\n"
            "- Your response: 'SEARCH_ACTIVITIES: Tokyo | I want activities in Tokyo for families'\n"
            "- User: 'Tell me about attractions in London'\n"
            "- Your response: 'SEARCH_ACTIVITIES: London | Tell me about attractions in London'\n\n"
            
            "FLIGHT SEARCH CAPABILITY:\n"
            "When a user asks about flights, mentions wanting to search for flights, or when you have complete travel data, you should request a flight search by responding with:\n"
            "SEARCH_FLIGHTS: origin|destination|departure_date|return_date|adults|travel_class\n"
            "For example:\n"
            "- User: 'Find me flights from JFK to LAX on 2025-03-15'\n"
            "- Your response: 'SEARCH_FLIGHTS: JFK|LAX|2025-03-15||1|Economy'\n"
            "- User: 'I need round trip flights from New York to London, leaving March 15 and returning March 22 for 2 people'\n"
            "- Your response: 'SEARCH_FLIGHTS: JFK|LHR|2025-03-15|2025-03-22|2|Economy'\n"
            "- User: 'Show me business class flights'\n"
            "- Your response: 'SEARCH_FLIGHTS: JFK|LAX|2025-03-15|2025-03-22|1|Business'\n\n"
            
            "IMPORTANT FLIGHT SEARCH RULES:\n"
            "- Use empty string (||) for return_date if one-way trip\n"
            "- Convert city names to airport codes (NYC→JFK, LA→LAX, London→LHR, Paris→CDG, etc.)\n"
            "- Valid travel classes: Economy, Premium Economy, Business, First\n"
            "- When you receive FLIGHT_SEARCH_RESULTS, use ONLY that flight data\n"
            "- Present flight results with prices, times, airlines, and durations clearly\n\n"
            
            "CRITICAL: When you receive ACTIVITY_SEARCH_RESULTS or FLIGHT_SEARCH_RESULTS, you MUST use ONLY the information from those search results. Do not add generic information or your own knowledge. Present the search results exactly as they are provided, including:\n"
            "- The overview/summary from the search\n"
            "- Each numbered recommendation with its exact title, score, description, and URL\n"
            "- The available images with their URLs\n"
            "- The search query that was used\n"
            "Format this information in a user-friendly way but do not modify or add to the content.\n\n"
            
            "COLLECTION PROCESS:\n"
            "Collect these details in a natural conversation (don't repeat questions if user already provided info):\n"
            "1. ORIGIN (where they're traveling FROM)\n"
            "2. DESTINATION (where they're traveling TO)\n"
            "3. NUMBER OF TRAVELERS\n"
            "4. DEPARTURE DATE\n"
            "5. RETURN DATE\n"
            "6. ACTIVITIES (optional - if they don't have preferences, offer recommendations)\n\n"
            
            "IMPORTANT RULES:\n"
            "- Be conversational and remember what the user has already told you\n"
            "- If user provides multiple details at once, acknowledge all of them and only ask for what's missing\n"
            "- Don't repeat questions for information already provided\n"
            "- Use your intelligence to understand context and determine when users are asking for activity information\n"
            "- Ask follow-up questions naturally, not like a form\n"
            "- When you receive search results, YOU MUST USE ONLY THAT DATA - no generic information\n\n"
            
            "CONVERSATION STYLE:\n"
            "- Be natural and engaging, like a helpful travel agent\n"
            "- Use emojis sparingly\n"
            "- Vary your language (don't sound robotic)\n"
            "- If user asks non-travel questions, gently redirect but stay friendly\n"
            "- Show excitement about destinations and activities\n\n"
            
            "AIRPORT CODES & DATES:\n"
            "- Convert city names to their main airport codes intelligently (e.g., 'New York' → 'JFK', 'Los Angeles' → 'LAX', 'London' → 'LHR')\n"
            "- Format ALL dates as YYYY-MM-DD (e.g., 'March 15th' → '2025-03-15', '12/25/2025' → '2025-12-25')\n"
            "- Use your intelligence to parse any date format users provide\n"
            "- If you're unsure about an airport code, use the most common/main airport for that city\n"
            "- Handle relative dates intelligently (e.g., 'next Friday', 'in 2 weeks') based on current date context\n\n"
            
            "WHEN TO PROVIDE JSON:\n"
            "Only when you have ALL required information (origin, destination, travelers, departure, return), respond with:\n"
            "TRAVEL_DATA_COMPLETE\n"
            "{\"origin\": \"AIRPORT_CODE\", \"destination\": \"AIRPORT_CODE\", \"travelers\": number, \"departure\": \"YYYY-MM-DD\", \"return\": \"YYYY-MM-DD\", \"activities\": \"preferences or recommendations\"}\n\n"
            
            "After providing travel data, you can offer to search for flights using the flight search capability.\n\n"
            "Continue the conversation normally after providing any search results."
        )
    }
]

def extract_ai_content(ai_response):
    """
    Extract the actual content from AI API response
    
    Args:
        ai_response: Raw AI response (could be dict or string)
        
    Returns:
        str: The actual AI message content
    """
    # If it's already a string, return it
    if isinstance(ai_response, str):
        return ai_response
    
    # If it's a dict (API response format), extract the content
    if isinstance(ai_response, dict):
        try:
            # Handle the specific API response format you're using
            if 'choices' in ai_response and len(ai_response['choices']) > 0:
                message = ai_response['choices'][0].get('message', {})
                return message.get('content', str(ai_response))
            else:
                return str(ai_response)
        except (KeyError, IndexError, TypeError):
            return str(ai_response)
    
    return str(ai_response)

@app.post("/chat")
async def chat_endpoint(req: Request):
    global chat_history
    
    try:
        data = await req.json()
        user_input = data.get("message", "")
        
        if not user_input:
            return {"reply": "Please provide a message!"}
        
        # Add user message to chat history
        chat_history.append({"role": "user", "content": user_input})
        
        # Get AI response
        raw_ai_reply = ask_ai_with_history(chat_history)
        ai_reply = extract_ai_content(raw_ai_reply)
        
        # Handle error responses from the AI
        if isinstance(ai_reply, str) and "⚠️ Error" in ai_reply:
            chat_history.append({"role": "assistant", "content": ai_reply})
            return {"reply": "I'm having trouble processing your request. Please try again!"}
        
        # Initialize response data
        activities_data = None
        flights_data = None
        final_reply = ai_reply
        
        # Check if AI is requesting an activity search
        if "SEARCH_ACTIVITIES:" in ai_reply:
            try:
                # Extract search parameters from AI response
                search_line = [line for line in ai_reply.split('\n') if 'SEARCH_ACTIVITIES:' in line][0]
                search_params = search_line.replace('SEARCH_ACTIVITIES:', '').strip()
                
                if '|' in search_params:
                    location, user_query = search_params.split('|', 1)
                    location = location.strip()
                    user_query = user_query.strip()
                else:
                    location = search_params.strip()
                    user_query = user_input
                
                print(f"🤖 AI requested search for location: '{location}', query: '{user_query}'")
                print(f"🔍 Initiating Tavily search...")
                
                # Validate Tavily API before making request
                if not validate_tavily_api():
                    final_reply = ai_reply.replace(search_line, "").strip()
                    if not final_reply:
                        final_reply = f"I'd love to help you find activities in {location}! Let me provide some general recommendations."
                else:
                    # Perform the search using the imported function
                    activities_data = search_activities(location, user_query=user_query)
                    
                    if activities_data:
                        print("✅ Search completed successfully!")
                        print(f"📊 Found {len(activities_data.get('results', []))} results")
                        
                        # Format the search results for the AI using the imported function
                        search_results = format_activities_response(activities_data)
                        
                        # Add search results to chat history and get AI's response with the data
                        chat_history.append({"role": "assistant", "content": ai_reply})
                        
                        search_instruction = (
                            f"Here are the current search results for {location}:\n\n{search_results}\n\n"
                            f"IMPORTANT: Please respond to the user using ONLY the information from these search results. "
                            f"Include the specific titles, descriptions, URLs, scores, and images from the search results. "
                            f"Format your response to show the user exactly what was found, including:\n"
                            f"- The overview/summary\n"
                            f"- Each numbered recommendation with its title, score, description, and URL\n"
                            f"- The available images\n"
                            f"- The search query that was used\n"
                            f"Anytime the image url is provided, put it in an image tag so that it can be displayed in the frontend.\n\n"
                            f"it should look something like this (<img src='the image url' alt='Description of image' style='border-radius: 10px; width: 50vw; height: auto;'>).\n\n"
                            f"DO NOT add generic information. Use only the data provided above."
                        )
                        
                        chat_history.append({"role": "user", "content": search_instruction})
                        
                        # Get AI's final response with the search data
                        raw_final_reply = ask_ai_with_history(chat_history)
                        final_reply = extract_ai_content(raw_final_reply)
                        
                        # Remove the search-related messages from history to keep it clean
                        chat_history = chat_history[:-2]
                    else:
                        print("❌ Search failed - no results returned")
                        final_reply = ai_reply.replace(search_line, "").strip()
                        if not final_reply:
                            final_reply = f"I'd love to help you find activities in {location}! Let me provide some general recommendations while I work on getting you more specific information."
                        
            except Exception as e:
                print(f"Error processing activity search: {e}")
                final_reply = ai_reply.split('SEARCH_ACTIVITIES:')[0].strip()
                if not final_reply:
                    final_reply = "I'd be happy to help you find activities! Could you tell me more about what you're looking for?"
        
        # Check if AI is requesting a flight search
        elif "SEARCH_FLIGHTS:" in ai_reply:
            try:
                # Extract flight search parameters
                search_line = [line for line in ai_reply.split('\n') if 'SEARCH_FLIGHTS:' in line][0]
                search_params = search_line.replace('SEARCH_FLIGHTS:', '').strip()
                
                # Parse parameters: origin|destination|departure_date|return_date|adults|travel_class
                params = search_params.split('|')
                if len(params) >= 3:
                    origin = params[0].strip()
                    destination = params[1].strip()
                    departure_date = params[2].strip()
                    return_date = params[3].strip() if len(params) > 3 and params[3].strip() else None
                    adults = int(params[4].strip()) if len(params) > 4 and params[4].strip() else 1
                    travel_class = params[5].strip() if len(params) > 5 and params[5].strip() else "Economy"
                    
                    print(f"🛫 AI requested flight search: {origin} → {destination}")
                    print(f"📅 Departure: {departure_date}, Return: {return_date}")
                    print(f"👥 Passengers: {adults}, Class: {travel_class}")
                    
                    if not validate_serpapi():
                        final_reply = ai_reply.replace(search_line, "").strip()
                        if not final_reply:
                            final_reply = f"I'd love to help you find flights from {origin} to {destination}! Let me provide some general guidance while I work on getting you specific flight information."
                    else:
                        # Perform flight search
                        flights_data = search_flights(origin, destination, departure_date, return_date, adults, travel_class)
                        
                        # Print results to terminal for debugging
                        if flights_data:
                            print_flights_to_terminal(flights_data)
                        
                        if flights_data and "error" not in flights_data:
                            print("✅ Flight search completed successfully!")
                            
                            # Format search results for AI
                            search_results = format_flights_response(flights_data)
                            
                            # Add search results to chat and get AI response
                            chat_history.append({"role": "assistant", "content": ai_reply})
                            
                            search_instruction = (
                                f"Here are the flight search results:\n\n{search_results}\n\n"
                                f"IMPORTANT: Please respond to the user using ONLY the flight information from these search results. "
                                f"Include specific prices, airlines, flight times, durations, and airport information. "
                                f"Format your response to show the user exactly what flights were found. "
                                f"Present the information in a clear, organized way with:\n"
                                f"- Flight prices and total duration\n"
                                f"- Airline names and flight numbers\n"
                                f"- Departure and arrival times with airport codes\n"
                                f"- Whether flights are direct or have layovers\n"
                                f"- Carbon emissions if available\n"
                                f"DO NOT add generic flight information. Use only the data provided above."
                            )
                            
                            chat_history.append({"role": "user", "content": search_instruction})
                            
                            # Get AI's final response with flight data
                            raw_final_reply = ask_ai_with_history(chat_history)
                            final_reply = extract_ai_content(raw_final_reply)
                            
                            # Clean up chat history
                            chat_history = chat_history[:-2]
                        else:
                            print("❌ Flight search failed")
                            error_msg = flights_data.get("error", "Unknown error") if flights_data else "No results returned"
                            print(f"Error details: {error_msg}")
                            
                            final_reply = ai_reply.replace(search_line, "").strip()
                            if not final_reply:
                                final_reply = f"I'm having trouble finding flights from {origin} to {destination} right now. This could be due to:\n\n" \
                                            f"• Invalid airport codes or city names\n" \
                                            f"• No flights available for the selected dates\n" \
                                            f"• API service temporarily unavailable\n\n" \
                                            f"Please try:\n" \
                                            f"• Different dates\n" \
                                            f"• Nearby airports\n" \
                                            f"• Or let me know if you'd like help with something else!"
                        
            except Exception as e:
                print(f"❌ Error processing flight search: {e}")
                final_reply = ai_reply.split('SEARCH_FLIGHTS:')[0].strip()
                if not final_reply:
                    final_reply = "I'd be happy to help you find flights! Could you tell me your departure and destination cities along with your travel dates?"
        
        # Check if data collection is complete and extract JSON if present
        travel_data = None
        data_complete = False
        
        if "TRAVEL_DATA_COMPLETE" in final_reply:
            try:
                # Extract JSON from the response
                json_start = final_reply.find("{")
                json_end = final_reply.rfind("}") + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = final_reply[json_start:json_end]
                    travel_data = json.loads(json_str)
                    data_complete = True
                    
                    print("🎯 Travel data collection complete! Auto-searching for flights and activities...")
                    
                    # IMPROVED: Auto-search for flights FIRST, then let AI use the results
                    if not flights_data and validate_serpapi():
                        origin = travel_data.get('origin', '')
                        destination = travel_data.get('destination', '')
                        departure = travel_data.get('departure', '')
                        return_date = travel_data.get('return', '')
                        travelers = travel_data.get('travelers', 1)
                        
                        if origin and destination and departure:
                            print(f"🛫 Auto-searching flights: {origin} → {destination}")
                            flights_data = search_flights(origin, destination, departure, return_date, travelers)
                            
                            if flights_data and "error" not in flights_data:
                                print("✅ Auto flight search successful!")
                                print_flights_to_terminal(flights_data)
                                
                                # Format flight results and let AI respond with them
                                flight_results = format_flights_response(flights_data)
                                
                                # Add the travel completion message to history
                                chat_history.append({"role": "assistant", "content": final_reply})
                                
                                # Give AI the flight results to incorporate
                                flight_instruction = (
                                    f"Great! I found flights for your trip. Here are the results:\n\n{flight_results}\n\n"
                                    f"Please create a comprehensive trip summary that includes:\n"
                                    f"1. The travel details you collected\n"
                                    f"2. The flight options from the search results above (include prices, times, airlines)\n"
                                    f"3. Offer to help with activities or other trip planning\n\n"
                                    f"Use ONLY the flight data provided above. Present it in a user-friendly format."
                                )
                                
                                chat_history.append({"role": "user", "content": flight_instruction})
                                
                                # Get AI response with flight data
                                raw_flight_reply = ask_ai_with_history(chat_history)
                                flight_enhanced_reply = extract_ai_content(raw_flight_reply)
                                
                                # Clean up chat history
                                chat_history = chat_history[:-2]
                                
                                # Update final reply with flight-enhanced version
                                final_reply = flight_enhanced_reply
                                
                            else:
                                print("❌ Auto flight search failed")
                                
                    # Auto-search for activities if we haven't already
                    if not activities_data and validate_tavily_api():
                        destination = travel_data.get('destination', '')
                        activities = travel_data.get('activities', '')
                        
                        if destination:
                            print(f"🔍 Auto-searching activities for: {destination}")
                            activities_data = search_activities(destination, activities)
                            
                            if activities_data:
                                print("✅ Auto activity search successful!")
                    
                    # Clean up the response to remove JSON for display
                    clean_reply = final_reply[:json_start].replace("TRAVEL_DATA_COMPLETE", "").strip()
                    
                    # If we don't have a clean reply, create a basic summary
                    if not clean_reply:
                        clean_reply = f"Perfect! I have all your travel details."
                    
                    # Update chat history with the clean response
                    chat_history.append({"role": "assistant", "content": clean_reply})
                    
                    return {
                        "reply": final_reply,  # This now includes flight info if found
                        "travel_data": travel_data,
                        "activities_data": activities_data,
                        "flights_data": flights_data,
                        "data_complete": True
                    }
                    
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing JSON: {e}")
                # Continue with normal flow if JSON parsing fails
        
        # Always add final AI response to chat history (if not already added above)
        if "TRAVEL_DATA_COMPLETE" not in final_reply:
            chat_history.append({"role": "assistant", "content": final_reply})
        
        # Keep chat history manageable (last 20 messages)
        if len(chat_history) > 21:  # 1 system message + 20 conversation messages
            chat_history = [chat_history[0]] + chat_history[-20:]
        
        return {
            "reply": final_reply, 
            "travel_data": travel_data,
            "activities_data": activities_data,
            "flights_data": flights_data,
            "data_complete": data_complete
        }
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return {"reply": "I encountered an unexpected error. Please try again!"}

@app.get("/")
async def root():
    return {"message": "AI Travel Agent Backend is running!"}

@app.post("/reset")
async def reset_chat():
    """Reset the chat history"""
    global chat_history
    
    chat_history = [chat_history[0]]  # Keep only the system message
    
    return {"message": "Chat reset successfully"}

@app.get("/health")
async def health_check():
    """Health check endpoint that validates both Tavily and SerpAPI"""
    tavily_status = "OK" if validate_tavily_api() else "No API Key"
    serpapi_status = "OK" if validate_serpapi() else "No API Key"
    
    return {
        "status": "healthy",
        "tavily_api": tavily_status,
        "serpapi": serpapi_status,
        "message": "AI Travel Agent Backend is running!"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)