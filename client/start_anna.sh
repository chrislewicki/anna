#!/bin/zsh

# Replace with your real command to start the model
ollama serve &

sleep 5

tailscale serve --http=11435 11434 &

# Notify VPS
curl -X POST http://anna-scaffold.snowy-hen.ts.net:5000/api/anna/status -d '{"online": true}' -H "Content-Type: application/json"

trap 'curl -X POST http://anna-scaffold.snowy-hen.ts.net:5000/api/anna/status -d "{\"online\": false}" -H "Content-Type: application/json" && exit' SIGINT SIGTERM
