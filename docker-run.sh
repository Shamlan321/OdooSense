#!/bin/bash

# Build the Docker image
docker build -t odoosense .

# Run with host network and environment file
docker run -i --rm \
  --net=host \
  --env-file .env \
  odoosense