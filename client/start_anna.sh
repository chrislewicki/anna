#!/bin/bash

# Replace with your real command to start the model
ollama run mistral &

sleep 5

# Notify VPS
curl -X POST https://your-vps/api/anna/status -d '{"online": true}' -H "Content-Type: application/json"
