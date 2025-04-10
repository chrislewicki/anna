#!/bin/bash

# Replace with your real command to start the model
ollama run mistral &

sleep 5

# Notify VPS
curl -X POST http://anna-scaffold.snowy-hen.ts.net:5000/api/anna/status -d '{"online": true}' -H "Content-Type: application/json"
