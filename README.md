# CodeReviewAutomation

A Git-based, LLM-powered code review tool for any language (C++, Python, Kotlin, etc.) supporting both **Azure OpenAI** and **Ollama/CodeLlama** as backends. It integrates with your Git workflow and blocks commits with critical issues.

---

## Features
- Reviews only changed (staged) files before commit
- Supports multiple languages (C++, Python, Kotlin, etc.)
- LLM backend: Azure OpenAI (preferred) or Ollama/CodeLlama (fallback)
- Blocks commit if critical (HIGH risk) issues are found or if review fails
- Simple, cross-platform Git hook setup
- Cross-platform: Linux, Mac, Windows (with PowerShell or Git Bash)

---

## 1. Ollama & CodeLlama Setup

### Install Ollama
- [Ollama installation guide](https://ollama.com/download)

### Pull CodeLlama Model
```sh
ollama pull codellama:latest
# or for a specific size
ollama pull codellama:7b
```

### Run Ollama
- **Linux/Mac:**
  ```sh
  ollama serve
  ```
- **Docker:**
  ```sh
  docker run -d -p 11434:11434 ollama/ollama
  ```

### Verify Model
```sh
ollama list
```
You should see `codellama:latest` or `codellama:7b` in the list.

---

## 2. Azure OpenAI Setup

1. Create an Azure OpenAI resource in the Azure portal.
2. Deploy a model (e.g., `gpt-4`, `gpt-35-turbo`).
3. Get your API key and endpoint from the Azure portal.

### Set Environment Variables

#### Linux/Mac (Bash):
```sh
export AZURE_OPENAI_API_KEY="your-azure-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
```

#### Windows (PowerShell):
```powershell
$env:AZURE_OPENAI_API_KEY = "your-azure-api-key"
$env:AZURE_OPENAI_ENDPOINT = "https://your-resource.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT = "your-deployment-name"
$env:AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
```

---

## 3. Fallback Logic
- The tool will try Azure OpenAI first (if all variables are set).
- If Azure is not available, it will fallback to Ollama/CodeLlama.
- If neither is available, the commit is blocked.

---

## 4. Environment Variables for Ollama

#### Linux/Mac:
```sh
export OLLAMA_URL="http://localhost:11434"
export OLLAMA_MODEL="codellama:latest"
```

#### Windows (PowerShell):
```powershell
$env:OLLAMA_URL = "http://localhost:11434"
$env:OLLAMA_MODEL = "codellama:latest"
```

---

## 5. Git Hooks Setup (Recommended: Manual Copy)

### A. Add the Pre-commit Hook
- This repository includes a sample pre-commit hook file in the `.githooks/` directory.
- **After cloning the repo, copy the hook to your local `.git/hooks/` directory:**

### **Linux/Mac/Git Bash:**
```sh
cp script-git/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### **Windows (PowerShell):**
```powershell
Copy-Item script-git/pre-commit .git/hooks/pre-commit
# No need for chmod on Windows
```

- Now, every time you run `git commit`, the code review will run automatically!

### Why this approach?
- **Simple:** No special git config or Python install step needed.
- **Cross-platform:** Works on Linux, Mac, and Windows (with Git Bash or PowerShell).
- **Easy to update:** Just copy the new hook if it changes.

---

## 6. Usage

### A. Stage Your Changes
```sh
git add .
```

### B. Commit
```sh
git commit -m "your message"
```
- The pre-commit hook will run the code review.
- If a HIGH risk is found or the review fails, the commit is blocked.

### C. Manual Review (Optional)
```sh
python code_reviewer.py --staged
```

---

## 7. Troubleshooting
- **Timeouts:** First LLM request may take a while as the model loads.
- **404 from Ollama:** Ensure the model name matches exactly what `ollama list` shows.
- **Azure errors:** Double-check your deployment name, endpoint, and API key.
- **Windows users:** Use PowerShell for setting environment variables.
- **No reviews generated:** The commit will be blocked if the review fails or LLM is unavailable.

---

## 8. Security
- Never commit your Azure API key or secrets to a public repo!
- Use environment variables or a `.env` file (add `.env` to `.gitignore`).

---

## 9. Author
[amitchaturvedi on GitHub](https://github.com/amitchaturvedi)

---

**Happy code reviewing!** 