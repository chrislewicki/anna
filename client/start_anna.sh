#!/bin/bash

# Replace with your real command to start the model
ollama run mistral &

sleep 5

# Notify VPS
curl -X POST https://anna-scaffold.snowy-hen.ts.net/api/anna/status -d '{"online": true}' -H "Content-Type: application/json"
