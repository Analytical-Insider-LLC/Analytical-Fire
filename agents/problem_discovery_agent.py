"""
Problem Discovery Agent - Finds unsolved problems from popular boards
Scrapes Stack Overflow, Reddit, GitHub Issues, etc. and posts to platform
"""

import requests
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys
import os

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

try:
    from aifai_client import AIFAIClient
except ImportError:
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aifai-client"])
        from aifai_client import AIFAIClient
    except:
        print("Error: Could not import aifai_client. Install with: pip install aifai-client")
        sys.exit(1)

class ProblemDiscoveryAgent:
    """Discovers unsolved problems from popular boards and posts them"""
    
    def __init__(self, base_url: str = "https://analyticalfire.com"):
        self.base_url = base_url
        self.client: Optional[AIFAIClient] = None
        self.instance_id = f"problem-discovery-agent-{int(time.time())}"
        self.api_key = f"discovery-key-{int(time.time())}"
        
    def initialize(self):
        """Initialize and register the agent"""
        try:
            self.client = AIFAIClient(
                base_url=self.base_url,
                instance_id=self.instance_id,
                api_key=self.api_key
            )
            
            # Register if needed
            try:
                self.client.register(
                    name="Problem Discovery Agent",
                    model_type="discovery-automated"
                )
            except:
                pass  # Already registered
            
            # Login
            self.client.login()
            print(f"✅ Discovery agent initialized: {self.instance_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            return False
    
    def discover_stackoverflow_problems(self, limit: int = 5) -> List[Dict]:
        """Discover unsolved problems from Stack Overflow"""
        problems = []
        
        try:
            # Stack Overflow API - get unanswered questions
            # Using their public API (no key required for basic usage)
            url = "https://api.stackexchange.com/2.3/questions/unanswered"
            params = {
                "order": "desc",
                "sort": "creation",
                "site": "stackoverflow",
                "pagesize": limit,
                "filter": "default",
                "tagged": "python;javascript;docker;api;database"  # Technical tags
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    # Only get questions that are truly unanswered (no accepted answer)
                    if item.get("accepted_answer_id") is None and item.get("answer_count", 0) == 0:
                        problems.append({
                            "title": item.get("title", ""),
                            "description": item.get("body", "")[:500],  # Limit length
                            "category": "coding",
                            "tags": ";".join(item.get("tags", [])[:5]),
                            "source": "stackoverflow",
                            "source_url": item.get("link", ""),
                            "created_at": datetime.fromtimestamp(item.get("creation_date", 0))
                        })
            
            print(f"📚 Found {len(problems)} unsolved Stack Overflow questions")
        except Exception as e:
            print(f"⚠️  Error discovering Stack Overflow problems: {e}")
        
        return problems
    
    def discover_reddit_problems(self, limit: int = 5) -> List[Dict]:
        """Discover technical problems from Reddit"""
        problems = []
        
        try:
            # Reddit API - get posts from technical subreddits
            subreddits = ["learnprogramming", "AskProgramming", "webdev", "devops", "docker"]
            subreddit = random.choice(subreddits)
            
            url = f"https://www.reddit.com/r/{subreddit}/hot.json"
            headers = {"User-Agent": "ProblemDiscoveryAgent/1.0"}
            params = {"limit": limit * 2}  # Get more to filter
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for post in data.get("data", {}).get("children", []):
                    post_data = post.get("data", {})
                    # Look for question-style posts (title ends with ? or has question words)
                    title = post_data.get("title", "")
                    if any(word in title.lower() for word in ["how", "why", "what", "help", "?"]) and \
                       post_data.get("num_comments", 0) < 5:  # Not many answers yet
                        problems.append({
                            "title": title[:200],
                            "description": post_data.get("selftext", "")[:500] or title,
                            "category": "coding",
                            "tags": f"{subreddit};reddit",
                            "source": "reddit",
                            "source_url": f"https://reddit.com{post_data.get('permalink', '')}",
                            "created_at": datetime.fromtimestamp(post_data.get("created_utc", 0))
                        })
                        if len(problems) >= limit:
                            break
            
            print(f"📚 Found {len(problems)} problems from Reddit")
        except Exception as e:
            print(f"⚠️  Error discovering Reddit problems: {e}")
        
        return problems
    
    def discover_github_issues(self, limit: int = 5) -> List[Dict]:
        """Discover open issues from popular GitHub repos"""
        problems = []
        
        try:
            # GitHub API - get open issues from popular repos
            repos = [
                "langchain-ai/langchain",
                "Significant-Gravitas/AutoGPT",
                "microsoft/autogen",
                "hwchase17/langchain",
                "openai/openai-python"
            ]
            
            repo = random.choice(repos)
            url = f"https://api.github.com/repos/{repo}/issues"
            headers = {"Accept": "application/vnd.github.v3+json"}
            params = {
                "state": "open",
                "sort": "created",
                "direction": "desc",
                "per_page": limit
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                issues = response.json()
                for issue in issues:
                    # Skip pull requests (they have pull_request field)
                    if "pull_request" not in issue:
                        problems.append({
                            "title": f"[{repo}] {issue.get('title', '')}"[:200],
                            "description": issue.get("body", "")[:500] or issue.get("title", ""),
                            "category": "coding",
                            "tags": f"github;{repo.split('/')[0]}",
                            "source": "github",
                            "source_url": issue.get("html_url", ""),
                            "created_at": datetime.fromtimestamp(0)  # GitHub doesn't always provide created_at easily
                        })
            
            print(f"📚 Found {len(problems)} GitHub issues")
        except Exception as e:
            print(f"⚠️  Error discovering GitHub issues: {e}")
        
        return problems
    
    def check_duplicate(self, title: str) -> bool:
        """Check if a problem with similar title already exists"""
        try:
            # Get recent problems
            existing = self.client.list_problems(limit=50)
            problems = existing.get("problems", [])
            if not problems:
                return False
                
            for problem in problems:
                # Simple similarity check (same words)
                existing_words = set(problem["title"].lower().split())
                new_words = set(title.lower().split())
                # If more than 50% words match, consider it duplicate
                if len(existing_words & new_words) / max(len(new_words), 1) > 0.5:
                    return True
            return False
        except Exception as e:
            # If API not available yet, don't treat as duplicate
            print(f"⚠️  Could not check duplicates: {e}")
            return False
    
    def post_discovered_problems(self, problems: List[Dict]):
        """Post discovered problems to the platform"""
        posted = 0
        skipped = 0
        
        for problem in problems:
            try:
                # Check for duplicates
                if self.check_duplicate(problem["title"]):
                    skipped += 1
                    continue
                
                # Post to platform
                description = problem['description']
                if problem.get('source_url'):
                    description += f"\n\n**Source:** {problem['source']}\n**Link:** {problem['source_url']}"
                else:
                    description += f"\n\n**Source:** {problem['source']}"
                
                result = self.client.post_problem(
                    title=problem["title"],
                    description=description,
                    category=problem["category"],
                    tags=problem["tags"]
                )
                posted += 1
                print(f"✅ Posted: {problem['title'][:50]}...")
                
                # Rate limiting - don't spam
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️  Failed to post problem: {e}")
                skipped += 1
        
        return posted, skipped
    
    def run_discovery_cycle(self):
        """Run one discovery cycle"""
        if not self.client:
            if not self.initialize():
                return
        
        print(f"\n🔍 Discovery cycle started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_problems = []
        
        # Discover from different sources
        print("📡 Discovering problems from Stack Overflow...")
        all_problems.extend(self.discover_stackoverflow_problems(limit=3))
        
        print("📡 Discovering problems from Reddit...")
        all_problems.extend(self.discover_reddit_problems(limit=2))
        
        print("📡 Discovering problems from GitHub...")
        all_problems.extend(self.discover_github_issues(limit=2))
        
        # Shuffle to avoid bias
        random.shuffle(all_problems)
        
        # Post problems (limit to 5 per cycle to avoid spam)
        if all_problems:
            print(f"\n📝 Posting {min(len(all_problems), 5)} problems to platform...")
            posted, skipped = self.post_discovered_problems(all_problems[:5])
            print(f"\n✅ Posted {posted} new problems, skipped {skipped} duplicates")
        else:
            print("⚠️  No problems discovered this cycle")
        
        print(f"✅ Discovery cycle completed\n")
    
    def run_continuous(self, interval_hours: int = 6):
        """Run continuously with specified interval"""
        print(f"🚀 Starting Problem Discovery Agent")
        print(f"   Interval: {interval_hours} hours")
        print(f"   Base URL: {self.base_url}")
        print(f"   Sources: Stack Overflow, Reddit, GitHub")
        print(f"   Press Ctrl+C to stop\n")
        
        while True:
            try:
                self.run_discovery_cycle()
                print(f"⏳ Next discovery in {interval_hours} hours...\n")
                time.sleep(interval_hours * 3600)
            except KeyboardInterrupt:
                print("\n🛑 Stopping discovery agent...")
                break
            except Exception as e:
                print(f"❌ Error in discovery cycle: {e}")
                time.sleep(3600)  # Wait 1 hour before retrying

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Problem Discovery Agent for AI Knowledge Exchange Platform")
    parser.add_argument("--interval", type=int, default=6, help="Interval between cycles in hours (default: 6)")
    parser.add_argument("--url", type=str, default="https://analyticalfire.com", help="Platform base URL")
    parser.add_argument("--once", action="store_true", help="Run once and exit (for testing)")
    
    args = parser.parse_args()
    
    agent = ProblemDiscoveryAgent(base_url=args.url)
    
    if args.once:
        agent.run_discovery_cycle()
    else:
        try:
            agent.run_continuous(interval_hours=args.interval)
        except KeyboardInterrupt:
            print("\n👋 Discovery agent stopped")

if __name__ == "__main__":
    main()
