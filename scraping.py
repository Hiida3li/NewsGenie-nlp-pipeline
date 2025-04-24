#!/usr/bin/env python3
"""
Enhanced News API Client - Process and save news articles with full content support
"""
import json
import csv
from datetime import datetime
import argparse
import logging
from pathlib import Path
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler


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


class NewsDataProcessor:
    """Handles loading, processing and exporting news data"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize processor with optional output directory"""
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(__name__)
        self.console = Console()
    
    def load_json(self, data_str: str) -> Dict[str, Any]:
        """Load data from JSON string"""
        try:
            return json.loads(data_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            raise
    
    def load_json_file(self, filepath: str) -> Dict[str, Any]:
        """Load data from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Failed to load JSON file: {e}")
            raise
    
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
        """Save data to JSON file"""
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
            # Write header with all fields
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
    
    def process_data(self, data: Dict[str, Any]) -> List[Article]:
        """Process raw news API data into article objects"""
        status = data.get("status")
        total_results = data.get("totalResults", 0)
        self.logger.info(f"API Status: {status}, Total Results: {total_results}")
        
        articles = [Article.from_dict(a) for a in data.get("articles", [])]
        self.logger.info(f"Processed {len(articles)} articles")
        return articles
    
    def process_and_save(self, data: Dict[str, Any], json_filename: Optional[str] = None, 
                         csv_filename: Optional[str] = None) -> tuple:
        """Process data and save to both JSON and CSV"""
        articles = self.process_data(data)
        json_path = self.save_json(data, json_filename)
        csv_path = self.save_csv(articles, csv_filename)
        return json_path, csv_path, articles


def display_articles(articles: List[Article], show_full_content: bool = False):
    """Display article information in a rich formatted table"""
    console = Console()
    table = Table(title="📰 News Articles Summary")
    
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Title", style="green", no_wrap=False)
    table.add_column("Source", style="yellow", no_wrap=True)
    table.add_column("Published", style="magenta", no_wrap=True)
    
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
        
        # Content handling
        if article.content:
            if show_full_content:
                console.print(f"   [yellow]Content:[/yellow] {article.content}")
            else:
                # Extract content before truncation marker if present
                content_preview = article.content.split('[+')[0] if '[+' in article.content else article.content
                console.print(f"   [yellow]Content Preview:[/yellow] {content_preview}")
                if '[+' in article.content:
                    console.print("   [dim](Full content available with --full-content flag)[/dim]")
        console.print("   ---")


def main():
    """Main entry point for the script"""
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Process and save news articles from JSON data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("input", nargs="?", 
                        help="JSON input (file path or raw JSON string)")
    parser.add_argument("--output-dir", "-o", 
                        help="Directory to save output files")
    parser.add_argument("--json", "-j", 
                        help="JSON output filename")
    parser.add_argument("--csv", "-s", 
                        help="CSV output filename")
    parser.add_argument("--quiet", "-q", action="store_true", 
                        help="Suppress console display output")
    parser.add_argument("--full-content", "-f", action="store_true",
                        help="Display full article content in console output")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    logger = logging.getLogger("news_processor")
    
    try:
        processor = NewsDataProcessor(args.output_dir)
        
        # Load data either from file or direct input
        if args.input:
            if Path(args.input).exists():
                logger.info(f"Loading JSON from file: {args.input}")
                data = processor.load_json_file(args.input)
            else:
                logger.info("Parsing JSON from input string")
                data = processor.load_json(args.input)
        else:
            # Read from stdin
            logger.info("Reading JSON from stdin")
            import sys
            data = processor.load_json(sys.stdin.read())
        
        # Process and save data
        json_path, csv_path, articles = processor.process_and_save(
            data, args.json, args.csv
        )
        
        # Display results
        if not args.quiet:
            display_articles(articles, args.full_content)
            logger.info(f"✅ Data saved to:")
            logger.info(f"   JSON: {json_path}")
            logger.info(f"   CSV: {csv_path}")
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON input")
        return 1
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

    