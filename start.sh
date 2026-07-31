#!/bin/bash
cd "/media/its_likesh/ML_Projects/college project/sem 6 project /Newsana"

echo "Starting Ollama on all interfaces..."
sudo pkill ollama 2>/dev/null
sleep 2
OLLAMA_HOST=0.0.0.0:11434 ollama serve &
sleep 4

echo "Starting Newsana..."
sudo docker compose up -d
sleep 5

echo "✅ Ready at http://localhost:5001"