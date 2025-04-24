import requests
import os
from dotenv import load_dotenv
import json
import csv
from datetime import datetime
import argparse

def fetch_news(keyword="Oman", language="ar", page_size=10):
    # Load environment variables from .env
    load_dotenv()
    
    # Get the API key from environment
    api_key = os.getenv("NEWS_API_KEY")
    
    # Make sure the key is loaded
    if not api_key:
        raise ValueError("NEWS_API_KEY not found in .env file.")
    
    # Use 'everything' endpoint to search news by keyword
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": keyword,
        "language": language,
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": api_key
    }
    
    # Send request
    response = requests.get(url, params=params)
    
    # Check if request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    
    # Convert response to JSON
    return response.json()

def save_to_json(data, filename=None):
    """Save data to JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_data_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename

def save_to_csv(data, filename=None):
    """Save articles to CSV file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_data_{timestamp}.csv"
    
    articles = data.get("articles", [])
    
    if not articles:
        print("No articles to save")
        return None
    
    # CSV header fields
    fields = ['title', 'source', 'author', 'description', 'url', 'publishedAt', 'content']
    
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(fields)
        
        # Write data
        for article in articles:
            writer.writerow([
                article.get('title', ''),
                article.get('source', {}).get('name', ''),
                article.get('author', ''),
                article.get('description', ''),
                article.get('url', ''),
                article.get('publishedAt', ''),
                article.get('content', '')
            ])
    
    return filename

def display_results(data):
    """Print headlines to console"""
    print("📰 Latest News Results:")
    
    articles = data.get("articles", [])
    if not articles:
        print("No articles found")
        return
    
    for i, article in enumerate(articles, start=1):
        print(f"{i}. {article.get('title')} - {article.get('source', {}).get('name')}")
        print(f"   Published: {article.get('publishedAt')}")
        print(f"   URL: {article.get('url')}")
        print()

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Fetch and save news articles")
    parser.add_argument("--keyword", "-k", default="Oman", help="Search keyword")
    parser.add_argument("--language", "-l", default="ar", help="Language code (e.g., ar, en)")
    parser.add_argument("--count", "-c", type=int, default=10, help="Number of articles to fetch")
    parser.add_argument("--json", "-j", help="JSON output filename (optional)")
    parser.add_argument("--csv", "-s", help="CSV output filename (optional)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress console output")
    
    args = parser.parse_args()
    
    # Fetch news data
    news_data = fetch_news(args.keyword, args.language, args.count)
    
    if news_data:
        # Save data
        json_file = save_to_json(news_data, args.json)
        csv_file = save_to_csv(news_data, args.csv)
        
        if not args.quiet:
            display_results(news_data)
            print(f"\nData saved to:")
            print(f"   JSON: {json_file}")
            print(f"   CSV: {csv_file}")

if __name__ == "__main__":
    main()