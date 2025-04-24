#!/usr/bin/env python3
"""
News API Client - Fetch and process news articles
"""
import requests
import os
from dotenv import load_dotenv
import json
import csv
from datetime import datetime
import argparse
import logging
from pathlib import Path
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler
import backoff


@dataclass
class Article:
    """Data class for article information"""
    title: str
    source: str
    source_id: Optional[str]
    author: Optional[str]
    description: Optional[str]
    url: str
    url_to_image: Optional[str]
    published_at: str
    content: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Article':
        """Create Article instance from API response dict"""
        return cls(
            title=data.get('title', ''),
            source=data.get('source', {}).get('name', ''),
            source_id=data.get('source', {}).get('id'),
            author=data.get('author'),
            description=data.get('description'),
            url=data.get('url', ''),
            url_to_image=data.get('urlToImage'),
            published_at=data.get('publishedAt', ''),
            content=data.get('content')
        )


class NewsApiClient:
    """Client for the News API"""
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from env or parameter"""
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
        if not self.api_key:
            raise ValueError("❌ NEWS_API_KEY not found in environment or .env file")
        
        self.logger = logging.getLogger(__name__)
        self.console = Console()
    
    @backoff.on_exception(backoff.expo, 
                          (requests.exceptions.RequestException, 
                           requests.exceptions.HTTPError),
                          max_tries=3)
    def fetch_everything(self, 
                         keyword: str = "Oman", 
                         language: str = "ar", 
                         page_size: int = 10) -> Dict[str, Any]:
        """Fetch articles from 'everything' endpoint with retry capability"""
        self.logger.info(f"Fetching news for keyword: '{keyword}' in {language}")
        
        url = f"{self.BASE_URL}/everything"
        params = {
            "q": keyword,
            "language": language,
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": self.api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raises exception for 4XX/5XX responses
        
        data = response.json()
        self.logger.info(f"Found {len(data.get('articles', []))} articles")
        return data
    
    def get_articles(self, 
                     keyword: str = "Oman", 
                     language: str = "ar", 
                     page_size: int = 10) -> List[Article]:
        """Get articles as structured objects"""
        data = self.fetch_everything(keyword, language, page_size)
        return [Article.from_dict(article) for article in data.get("articles", [])]


class NewsDataExporter:
    """Handles exporting news data to different formats"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize exporter with optional output directory"""
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(__name__)
    
    def _get_filename(self, base_name: Optional[str], extension: str) -> Path:
        """Generate filename with timestamp if none provided"""
        if base_name:
            filename = Path(base_name)
            if not filename.suffix:
                filename = filename.with_suffix(f".{extension}")
        else:
            filename = Path(f"news_data_{self.timestamp}.{extension}")
        
        return self.output_dir / filename
    
    def save_json(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save raw API response to JSON file"""
        file_path = self._get_filename(filename, "json")
        self.logger.info(f"Saving JSON data to {file_path}")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def save_csv(self, articles: List[Article], filename: Optional[str] = None) -> Path:
        """Save articles to CSV file"""
        file_path = self._get_filename(filename, "csv")
        self.logger.info(f"Saving CSV data to {file_path}")
        
        if not articles:
            self.logger.warning("No articles to save")
            return file_path
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['title', 'source', 'source_id', 'author', 'description', 
                            'url', 'url_to_image', 'publishedAt', 'content'])
            
            # Write data
            for article in articles:
                writer.writerow([
                    article.title,
                    article.source,
                    article.source_id or '',
                    article.author or '',
                    article.description or '',
                    article.url,
                    article.url_to_image or '',
                    article.published_at,
                    article.content or ''
                ])
        
        return file_path


def display_results(articles: List[Article]):
    """Display article information in a rich formatted table"""
    console = Console()
    table = Table(title="📰 Latest News Results")
    
    table.add_column("#", style="cyan")
    table.add_column("Title", style="green", no_wrap=False)
    table.add_column("Source", style="yellow")
    table.add_column("Published", style="magenta")
    
    if not articles:
        console.print("[yellow]No articles found[/yellow]")
        return
    
    for i, article in enumerate(articles, start=1):
        table.add_row(
            str(i),
            article.title,
            article.source,
            article.published_at
        )
    
    console.print(table)
    
    # Print more detailed information
    console.print("\n[bold]Article Details:[/bold]")
    for i, article in enumerate(articles, start=1):
        console.print(f"\n[cyan]{i}. [bold]{article.title}[/bold][/cyan]")
        console.print(f"   [yellow]Source:[/yellow] {article.source}")
        if article.author:
            console.print(f"   [yellow]Author:[/yellow] {article.author}")
        if article.description:
            console.print(f"   [yellow]Description:[/yellow] {article.description}")
        console.print(f"   [yellow]Published:[/yellow] {article.published_at}")
        console.print(f"   [yellow]URL:[/yellow] [link={article.url}]{article.url}[/link]")
        if article.url_to_image:
            console.print(f"   [yellow]Image:[/yellow] [link={article.url_to_image}]{article.url_to_image}[/link]")
        if article.content:
            content_preview = article.content.split('[+')[0] if '[+' in article.content else article.content
            console.print(f"   [yellow]Content Preview:[/yellow] {content_preview}")


def main():
    """Main entry point for the script"""
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Fetch and save news articles",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--keyword", "-k", default="Oman", 
                        help="Search keyword")
    parser.add_argument("--language", "-l", default="ar", 
                        help="Language code (e.g., ar, en)")
    parser.add_argument("--count", "-c", type=int, default=10, 
                        help="Number of articles to fetch")
    parser.add_argument("--output-dir", "-o", 
                        help="Directory to save output files")
    parser.add_argument("--json", "-j", 
                        help="JSON output filename (optional)")
    parser.add_argument("--csv", "-s", 
                        help="CSV output filename (optional)")
    parser.add_argument("--quiet", "-q", action="store_true", 
                        help="Suppress console display output")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--full-content", "-f", action="store_true",
                        help="Display full article content in console output")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    logger = logging.getLogger("news_client")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize client and fetch news
        news_client = NewsApiClient()
        raw_data = news_client.fetch_everything(
            args.keyword, args.language, args.count
        )
        
        # Process API response metadata
        status = raw_data.get("status")
        total_results = raw_data.get("totalResults", 0)
        logger.info(f"API Status: {status}, Total Results: {total_results}")
        
        # Convert to Article objects
        articles = [Article.from_dict(a) for a in raw_data.get("articles", [])]
        
        # Save data
        exporter = NewsDataExporter(args.output_dir)
        json_file = exporter.save_json(raw_data, args.json)
        csv_file = exporter.save_csv(articles, args.csv)
        
        # Display results
        if not args.quiet:
            display_results(articles)
            if args.full_content:
                console = Console()
                console.print("\n[bold]Full Article Content:[/bold]")
                for i, article in enumerate(articles, start=1):
                    console.print(f"\n[cyan]{i}. {article.title}[/cyan]")
                    if article.content:
                        console.print(f"[yellow]Content:[/yellow] {article.content}")
                    else:
                        console.print("[yellow]No content available[/yellow]")
                    console.print("---")
            
            logger.info(f"✅ Data saved to:")
            logger.info(f"   JSON: {json_file}")
            logger.info(f"   CSV: {csv_file}")
            
    except ValueError as e:
        logger.error(f"{e}")
        return 1
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())