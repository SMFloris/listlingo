# Shopping List Generator

This web application transforms raw user input into a clean, organized shopping list using the Qwen3:30b-a3b model from Ollama.

## Features

- Converts unstructured shopping list input into a formatted list
- Automatically categorizes and sorts items
- Generates funny, movie-themed names and summaries for shopping lists
- Saves checklists with their items in a database
- Allows viewing and updating checklist items

## How It Works

1. Users input their shopping list items in natural language
2. The app processes the input using the Qwen3:30b-a3b model
3. The model returns a formatted shopping list
4. The app generates a funny name and summary for the list
5. The checklist is saved in a database with its items
6. Users can view and update their checklists

## Requirements

- Python 3.11+
- Ollama with Qwen3:30b-a3b model installed
- SQLite database

## Usage

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Start Ollama and ensure the Qwen3:30b-a3b model is available
4. Run the app: `python app.py`
5. Access the app at `http://localhost:3030`

## Project Info

This project was an experiment using Aider chat and Qwen3:30b-a3b model. I was very pleased with the result - 90% of the code was written by AI.

## 🐳 Docker Support

### Build the Docker Image

```bash
docker build -t shopping-list-app .
```

### Run the Container

```bash
docker run -d \
  -p 3030:3030 \
  -e OLLAMA_URL="http://host.docker.internal:11434/api/generate" \
  -v $(pwd)/db:/app/db \
  --name shopping-list-app \
  shopping-list-app
```

**Notes:**
- Ensure Ollama is running on your host machine with the `qwen3:30b-a3b` model
- The `-v` flag persists the database across container restarts
- `host.docker.internal` allows the container to reach Ollama on the host
