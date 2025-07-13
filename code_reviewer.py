#!/usr/bin/env python3
"""
Git-Based LLM Code Review Agent
Reviews staged/modified files during git operations using OLLAMA/LLAMA3 or Azure OpenAI
"""

import os
import sys
import json
import subprocess
import requests
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

try:
    from openai import AzureOpenAI
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

class CodeReviewConfig:
    """Configuration for the code review agent"""
    
    def __init__(self):
        # LLM Configuration
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'codellama:latest')
        
        # Azure OpenAI Configuration
        self.azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.azure_api_key = os.getenv('AZURE_OPENAI_API_KEY')
        self.azure_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
        self.azure_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')
        
        # File patterns to review
        self.code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', 
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.html', '.css', '.scss', '.sql', '.sh', '.yaml', '.yml', '.json'
        }
        
        # Review settings
        self.max_file_size = int(os.getenv('MAX_FILE_SIZE', '50000'))  # 50KB default
        self.review_threshold = os.getenv('REVIEW_THRESHOLD', 'medium')  # low, medium, high

class GitOperations:
    """Git operations for file analysis"""
    
    @staticmethod
    def is_git_repo() -> bool:
        """Check if current directory is a git repository"""
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], 
                         capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def get_staged_files() -> List[str]:
        """Get list of staged files"""
        try:
            result = subprocess.run(['git', 'diff', '--cached', '--name-only'], 
                                  capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
            return [f.strip() for f in result.stdout.split('\n') if f.strip()]
        except subprocess.CalledProcessError:
            return []
    
    @staticmethod
    def get_modified_files() -> List[str]:
        """Get list of modified files (not staged)"""
        try:
            result = subprocess.run(['git', 'diff', '--name-only'], 
                                  capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
            return [f.strip() for f in result.stdout.split('\n') if f.strip()]
        except subprocess.CalledProcessError:
            return []
    
    @staticmethod
    def get_file_diff(filepath: str, staged: bool = True) -> str:
        """Get diff for a specific file"""
        try:
            cmd = ['git', 'diff', '--cached' if staged else '', filepath]
            cmd = [c for c in cmd if c]  # Remove empty strings
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    @staticmethod
    def get_file_content(filepath: str, staged: bool = True) -> str:
        """Get file content (staged version or working directory)"""
        try:
            if staged:
                # Get staged version
                result = subprocess.run(['git', 'show', f':{filepath}'], 
                                      capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
                return result.stdout
            else:
                # Get working directory version
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

class LLMClient:
    """Client for interacting with LLM services"""
    
    def __init__(self, config: CodeReviewConfig):
        self.config = config
        self.azure_client = None
        
        if AZURE_AVAILABLE and self.config.azure_api_key and self.config.azure_endpoint:
            try:
                self.azure_client = AzureOpenAI(
                    azure_endpoint=self.config.azure_endpoint,
                    api_key=self.config.azure_api_key,
                    api_version=self.config.azure_api_version
                )
                print("✓ Azure OpenAI client initialized")
            except Exception as e:
                print(f"⚠ Azure OpenAI initialization failed: {e}")
    
    def is_ollama_available(self) -> bool:
        """Check if OLLAMA is running and accessible"""
        try:
            response = requests.get(f"{self.config.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def is_azure_available(self) -> bool:
        """Check if Azure OpenAI is available"""
        return self.azure_client is not None
    
    def generate_review_ollama(self, content: str, filename: str, diff: str = "") -> Optional[str]:
        """Generate code review using OLLAMA"""
        try:
            prompt = self._create_review_prompt(content, filename, diff)
            
            payload = {
                "model": self.config.ollama_model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(
                f"{self.config.ollama_url}/api/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                print(f"OLLAMA API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error calling OLLAMA: {e}")
            return None
    
    def generate_review_azure(self, content: str, filename: str, diff: str = "") -> Optional[str]:
        """Generate code review using Azure OpenAI"""
        try:
            prompt = self._create_review_prompt(content, filename, diff)
            
            response = self.azure_client.chat.completions.create(
                model=self.config.azure_deployment,
                messages=[
                    {"role": "system", "content": "You are an expert code reviewer. Provide constructive, detailed code reviews focusing on the changes made."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            return None
    
    def generate_review(self, content: str, filename: str, diff: str = "") -> Optional[str]:
        """Generate code review using available LLM service"""
        # Try Azure OpenAI first if available
        if self.is_azure_available():
            review = self.generate_review_azure(content, filename, diff)
            if review:
                return review
        
        # Fallback to OLLAMA
        if self.is_ollama_available():
            return self.generate_review_ollama(content, filename, diff)
        else:
            return None
    
    def _create_review_prompt(self, content: str, filename: str, diff: str = "") -> str:
        """Create a comprehensive code review prompt"""
        file_ext = Path(filename).suffix
        
        prompt = f"""Please provide a focused code review for the file: {filename}

**File Content:**
```{file_ext[1:] if file_ext else 'text'}
{content}
```
"""
        
        if diff:
            prompt += f"""
**Changes Made (Git Diff):**
```diff
{diff}
```

**Focus your review on the changes highlighted in the diff above.**
"""
        
        prompt += """
**Review Guidelines:**
1. **Primary Focus**: Review the specific changes made (if diff provided)
2. **Code Quality**: Check for readability, maintainability, and best practices
3. **Security**: Identify potential security vulnerabilities
4. **Performance**: Look for performance issues and optimization opportunities
5. **Bugs**: Spot potential bugs or logical errors
6. **Style**: Comment on code style and conventions adherence
7. **Testing**: Suggest if tests are needed for the changes

**Format your review as:**
- **Overall Assessment**: Brief summary of the changes/file
- **Issues Found**: List specific problems (if any)
- **Suggestions**: Actionable improvement recommendations
- **Positive Notes**: What's done well
- **Risk Level**: LOW/MEDIUM/HIGH based on potential impact

Be constructive, specific, and focus on what matters most for code quality and maintainability.
"""
        
        return prompt

class CodeReviewer:
    """Main code review orchestrator"""
    
    def __init__(self):
        self.config = CodeReviewConfig()
        self.llm_client = LLMClient(self.config)
        self.git_ops = GitOperations()
    
    def should_review_file(self, filepath: str) -> bool:
        """Determine if a file should be reviewed"""
        path = Path(filepath)
        
        # Explicitly skip deleted files
        if not path.exists():
            return False

        # Check if it's a code file
        if path.suffix not in self.config.code_extensions:
            return False
        
        # Check file size
        try:
            if path.exists() and path.stat().st_size > self.config.max_file_size:
                return False
        except:
            pass
        
        # Skip review files themselves
        if path.name.endswith('.review.md'):
            return False
        
        return True
    
    def review_files(self, files: List[str], staged: bool = True) -> Dict[str, str]:
        """Review a list of files"""
        reviews = {}
        
        for filepath in files:
            if not self.should_review_file(filepath):
                continue
            
            print(f"📝 Reviewing: {filepath}")
            
            # Get file content and diff
            content = self.git_ops.get_file_content(filepath, staged)
            diff = self.git_ops.get_file_diff(filepath, staged)
            
            if not content:
                print(f"⚠ Could not read content for {filepath}")
                continue
            
            # Generate review
            review = self.llm_client.generate_review(content, filepath, diff)
            
            if review:
                reviews[filepath] = review
                print(f"✅ Review completed for {filepath}")
            else:
                print(f"❌ Review failed for {filepath}")
        
        return reviews
    
    def save_reviews(self, reviews: Dict[str, str], output_dir: str = "."):
        """Save reviews to files"""
        output_path = Path(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for filepath, review in reviews.items():
            # Create review filename
            path = Path(filepath)
            review_filename = f"{path.name}.review.md"
            review_path = output_path / review_filename
            
            # Write review file
            review_content = f"""# Code Review: {filepath}

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Tool:** Git-Based LLM Code Review Agent
**Commit:** {self._get_current_commit_hash()}

---

{review}

---

*This review was automatically generated during git operations.*
"""
            
            with open(review_path, 'w', encoding='utf-8') as f:
                f.write(review_content)
            
            print(f"💾 Review saved: {review_path}")
    
    def _get_current_commit_hash(self) -> str:
        """Get current commit hash"""
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()[:8]
        except:
            return "unknown"

def install_git_hooks():
    """Install git hooks for automatic code review"""
    
    hooks_dir = Path('.git/hooks')
    if not hooks_dir.exists():
        print("❌ Not a git repository or .git/hooks directory not found")
        return False
    
    # Pre-commit hook
    pre_commit_hook = hooks_dir / 'pre-commit'
    pre_commit_content = '''#!/bin/bash
# Auto-generated LLM Code Review pre-commit hook
# This hook reviews only staged files and blocks commit if HIGH risk issues are found.

echo "🔍 Running LLM Code Review on staged files..."
python3 "$(git rev-parse --show-toplevel)/code_reviewer.py" --hook pre-commit

# Check if reviews indicate high risk
if [ -f ".review_result" ]; then
    RISK_LEVEL=$(cat .review_result)
    if [ "$RISK_LEVEL" = "HIGH" ]; then
        echo "❌ Commit blocked: HIGH RISK changes detected. Please review the generated .review.md files."
        rm -f .review_result
        exit 1
    fi
    rm -f .review_result
fi

echo "✅ Code review completed"
'''
    
    # Write pre-commit hook
    with open(pre_commit_hook, 'w', encoding="utf-8") as f:
        f.write(pre_commit_content)
    
    # Make executable
    pre_commit_hook.chmod(0o755)
    
    print("✅ Git hooks installed successfully!")
    print("📝 Reviews will be generated automatically on commit and commits will be blocked if HIGH risk issues are found.")
    return True

def main():
    parser = argparse.ArgumentParser(description='Git-Based LLM Code Review Agent')
    parser.add_argument('--hook', choices=['pre-commit', 'post-commit'], 
                       help='Run as git hook')
    parser.add_argument('--staged', action='store_true', default=True,
                       help='Review staged files (default)')
    parser.add_argument('--modified', action='store_true',
                       help='Review modified files (not staged)')
    parser.add_argument('--install-hooks', action='store_true',
                       help='Install git hooks for automatic review')
    parser.add_argument('--output-dir', default='.',
                       help='Directory to save review files')
    
    args = parser.parse_args()
    
    print("🚀 Git-Based LLM Code Review Agent")
    print("=" * 50)
    
    # Check if in git repository
    if not GitOperations.is_git_repo():
        print("❌ Not in a git repository")
        sys.exit(1)
    
    # Install hooks if requested
    if args.install_hooks:
        install_git_hooks()
        return
    
    # Initialize reviewer
    reviewer = CodeReviewer()
    
    # Check LLM availability
    if not reviewer.llm_client.is_azure_available() and not reviewer.llm_client.is_ollama_available():
        print("❌ No LLM service available!")
        print("Please configure Azure OpenAI or start OLLAMA")
        sys.exit(1)
    
    # Get files to review
    if args.modified:
        files = GitOperations.get_modified_files()
        staged = False
        print(f"📁 Found {len(files)} modified files")
    else:
        files = GitOperations.get_staged_files()
        staged = True
        print(f"📁 Found {len(files)} staged files")
    
    if not files:
        print("✅ No files to review")
        return
    
    # Review files
    reviews = reviewer.review_files(files, staged)
    
    if reviews:
        # Save reviews
        reviewer.save_reviews(reviews, args.output_dir)
        
        # For git hooks, check risk levels
        if args.hook:
            high_risk_found = any('HIGH' in review.upper() for review in reviews.values())
            with open('.review_result', 'w') as f:
                f.write('HIGH' if high_risk_found else 'LOW')
        
        print(f"\n✅ Generated {len(reviews)} code reviews")
    else:
        print("❌ No reviews generated")

if __name__ == "__main__":
    main()