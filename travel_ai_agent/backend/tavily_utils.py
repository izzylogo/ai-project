import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def search_activities(destination: str, activities: str = "", user_query: str = ""):
    """
    Search for activities and attractions using Tavily API
    
    Args:
        destination (str): The destination to search for
        activities (str): Specific activity preferences (optional)
        user_query (str): The original user query (optional)
    
    Returns:
        dict: Tavily API response with search results, or None if error
    """
    try:
        # Create a comprehensive search query based on user input
        if user_query and destination:
            # Use the user's specific query with the destination
            query = f"{user_query} {destination} travel guide attractions activities"
        elif activities and activities.lower() not in ['none', 'n/a', 'no preference']:
            query = f"best {activities} and attractions in {destination} travel guide"
        else:
            query = f"top tourist attractions and activities in {destination} travel guide sightseeing"
        
        print(f"Tavily search query: {query}")
        
        url = "https://api.tavily.com/search"
        headers = {
            "Authorization": f"Bearer {TAVILY_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "query": query,
            "search_depth": "advanced",
            "max_results": 5,
            "include_images": True,
            "include_answer": True,
            "include_raw_content": False
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            print_search_results_to_terminal(result, destination)
            return result
        else:
            print(f"Tavily API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error in Tavily search: {e}")
        return None

def format_activities_response(activities_data):
    """
    Format the activities search results for the AI to use - IMPROVED VERSION
    
    Args:
        activities_data (dict): Raw Tavily API response
    
    Returns:
        str: Formatted search results for AI consumption
    """
    if not activities_data or not activities_data.get('results'):
        return "No detailed activity results found."
    
    formatted_results = "ACTIVITY_SEARCH_RESULTS:\n\n"
    
    # Add the AI-generated answer if available
    if activities_data.get('answer'):
        formatted_results += f"**OVERVIEW:** {activities_data['answer']}\n\n"
    
    formatted_results += "**TOP RECOMMENDATIONS FROM SEARCH:**\n\n"
    
    for i, result in enumerate(activities_data['results'][:5], 1):
        title = result.get('title', 'Activity')
        url = result.get('url', '')
        content = result.get('content', '')
        score = result.get('score', 'N/A')
        
        # Clean and truncate content but keep it substantial
        if content:
            content = content[:400] + "..." if len(content) > 400 else content
        else:
            content = "Great place to visit!"
        
        formatted_results += f"**{i}. {title}**\n"
        formatted_results += f"   **Score:** {score}\n"
        formatted_results += f"   **Description:** {content}\n"
        if url:
            formatted_results += f"   **URL:** {url}\n"
        formatted_results += "\n"
    
    # Add images info if available
    if activities_data.get('images'):
        formatted_results += f"**AVAILABLE IMAGES:** {len(activities_data['images'])} photos\n"
        for i, image_url in enumerate(activities_data['images'][:3], 1):
            formatted_results += f"   {i}. {image_url}\n"
        formatted_results += "\n"
    
    # Add search query info
    if activities_data.get('query'):
        formatted_results += f"**SEARCH QUERY USED:** {activities_data['query']}\n\n"
    
    # IMPORTANT: Add specific instruction for AI
    formatted_results += "**INSTRUCTION FOR AI:** Please use the above search results to provide specific recommendations to the user. Include the actual titles, descriptions, URLs, and images from the search results. Do not generate generic information - use only the data provided above."
    
    return formatted_results

def format_activities_for_user(activities_data, destination):
    """
    Format activities data for direct user display (used in travel summary)
    
    Args:
        activities_data (dict): Raw Tavily API response
        destination (str): The destination name
    
    Returns:
        str: User-friendly formatted activities section
    """
    if not activities_data or not activities_data.get('results'):
        return f"\n\n🎯 **Activities for {destination}:**\nI'll help you find amazing activities once we start planning your itinerary!"
    
    activities_section = f"\n\n🎯 **Recommended Activities & Attractions in {destination}:**\n"
    
    # Add overview if available
    if activities_data.get('answer'):
        activities_section += f"\n📋 **Overview:** {activities_data['answer']}\n"
    
    activities_section += "\n🌟 **Top Recommendations:**\n"
    
    for i, result in enumerate(activities_data['results'][:5], 1):
        title = result.get('title', 'Activity')
        url = result.get('url', '')
        content = result.get('content', '')
        score = result.get('score', 'N/A')
        
        # Clean and truncate content
        if content:
            content = content[:300] + "..." if len(content) > 300 else content
        else:
            content = "Great destination to explore!"
        
        activities_section += f"\n**{i}. {title}** (Score: {score})\n"
        activities_section += f"📝 {content}\n"
        if url:
            activities_section += f"🔗 [Learn more]({url})\n"
    
    # Add images if available
    if activities_data.get('images'):
        activities_section += f"\n📸 **Destination Images:** {len(activities_data['images'])} photos available\n"
        for i, image_url in enumerate(activities_data['images'][:3], 1):
            activities_section += f"   {i}. ![Image {i}]({image_url})\n"
    
    return activities_section

def print_search_results_to_terminal(activities_data, destination):
    """
    Print search results to terminal in a nice format
    
    Args:
        activities_data (dict): Raw Tavily API response
        destination (str): The destination that was searched
    """
    print("\n" + "="*80)
    print(f"🔍 TAVILY SEARCH RESULTS FOR: {destination.upper()}")
    print("="*80)
    
    if not activities_data or not activities_data.get('results'):
        print("❌ No results found")
        print("="*80 + "\n")
        return
    
    # Print overview/answer if available
    if activities_data.get('answer'):
        print(f"\n📋 OVERVIEW:")
        print("-" * 40)
        print(f"{activities_data['answer']}")
    
    # Print search results
    results = activities_data.get('results', [])
    print(f"\n🌟 TOP {len(results)} RECOMMENDATIONS:")
    print("-" * 40)
    
    for i, result in enumerate(results, 1):
        title = result.get('title', 'Unknown Activity')
        url = result.get('url', 'No URL')
        content = result.get('content', 'No description available')
        score = result.get('score', 'N/A')
        
        print(f"\n{i}. {title}")
        print(f"   Score: {score}")
        print(f"   URL: {url}")
        print(f"   Description: {content[:200]}{'...' if len(content) > 200 else ''}")
    
    # Print additional info
    if activities_data.get('images'):
        print(f"\n📸 IMAGES AVAILABLE: {len(activities_data['images'])} photos")
        for i, image in enumerate(activities_data['images'][:3], 1):  # Show first 3 image URLs
            print(f"   {i}. {image}")
    
    # Print query info
    if activities_data.get('query'):
        print(f"\n🔎 SEARCH QUERY USED: {activities_data['query']}")
    
    # Print response time and follow-up URLs if available
    if activities_data.get('follow_up_questions'):
        print(f"\n❓ SUGGESTED FOLLOW-UP QUESTIONS:")
        for i, question in enumerate(activities_data['follow_up_questions'][:3], 1):
            print(f"   {i}. {question}")
    
    print("\n" + "="*80 + "\n")

def validate_tavily_api():
    """
    Validate that Tavily API key is available
    
    Returns:
        bool: True if API key is available, False otherwise
    """
    if not TAVILY_API_KEY:
        print("Warning: TAVILY_API_KEY not found in environment variables")
        return False
    return True