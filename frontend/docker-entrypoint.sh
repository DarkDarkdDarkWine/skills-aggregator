#!/bin/sh

until nc -z backend 8080; do
  echo "Waiting for backend..."
  sleep 2
done

echo "Backend is ready, starting nginx..."
exec nginx -g 'daemon off;'
