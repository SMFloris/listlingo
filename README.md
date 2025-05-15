# Shopping List Generator

A web application that transforms unstructured shopping list input into organized, categorized shopping lists using the Qwen3:30b-a3b model running on Ollama.

## Overview

This project demonstrates natural language processing capabilities for shopping list organization. It provides a RESTful API for managing shopping lists with features including item categorization, structured formatting, and creative naming.

## Features

- Natural language input processing for shopping lists
- Automatic item categorization and sorting
- AI-generated creative names and summaries
- Persistent checklist storage with SQLite
- RESTful API for checklist management
- Docker containerization support

## Getting Started

### Prerequisites

- Python 3.11+
- Ollama runtime with Qwen3:30b-a3b model
- SQLite database (included in repository)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/shopping-list-generator.git
cd shopping-list-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start Ollama and ensure the Qwen3:30b-a3b model is available:
```bash
ollama run qwen3:30b-a3b
```

## Usage

### Running Locally

```bash
python app.py
```

Access the application at `http://localhost:3030`

### Docker Support

Build the Docker image:
```bash
docker build -t shopping-list-app .
```

Run the container:
```bash
docker run -d \
  -p 3030:3030 \
  -e OLLAMA_URL="http://host.docker.internal:11434/api/generate" \
  -v $(pwd)/db:/app/db \
  --name shopping-list-app \
  shopping-list-app
```

## Architecture

1. User submits unstructured shopping list input
2. Application processes input using Qwen3:30b-a3b model
3. Model returns structured shopping list format
4. Application generates creative name/summary pair
5. Checklist stored in SQLite database
6. Users can view and update checklists via API

## Contributing

Please read our [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
