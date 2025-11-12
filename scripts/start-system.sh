#!/bin/bash
# Start the Wheel Analyzer development system
# This script starts Docker services (PostgreSQL and Redis) and optionally the Django dev server

set -e  # Exit on error

echo "🚀 Starting Wheel Analyzer System..."

# Start Docker services (PostgreSQL and Redis)
echo "📦 Starting Docker services (PostgreSQL and Redis)..."
docker-compose up -d

# Wait a moment for services to be ready
sleep 2

# Check if services are running
echo "✅ Checking service status..."
docker-compose ps

echo ""
echo "✅ System started successfully!"
echo ""
echo "Services running:"
echo "  - PostgreSQL: localhost:65432"
echo "  - Redis: localhost:36379"
echo ""
echo "To start the Django development server, run:"
echo "  just run"
echo ""
