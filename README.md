# Scripe - B2B Lead Generation Platform

Scripe is a standalone B2B lead generation system that helps find business contacts across Europe.

## Features

- AI-powered search query interpretation (multilingual: DE, EN, IT, FR)
- European-wide business search (DACH, Italy, France, etc.)
- Quality tier-based lead generation
- REST API for external integrations
- Real-time search progress via SSE

## Architecture

```
scripe-standalone/
├── backend/           # FastAPI Python Backend
│   ├── src/app/       # Application code
│   └── Dockerfile
├── frontend/          # React TypeScript Frontend
│   ├── src/           # React components
│   └── Dockerfile
├── nginx/             # Reverse proxy config
├── docker-compose.yml # Development setup
└── docker-compose.prod.yml # Production setup
```

## Quick Start (Development)

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USER/scripe-standalone.git
cd scripe-standalone

# 2. Copy environment file
cp .env.example .env
# Edit .env with your API keys

# 3. Start with Docker Compose
docker compose up -d --build

# 4. Open in browser
# Frontend: http://localhost:3005
# Backend API: http://localhost:8010/api/docs
```

## Production Deployment (Hetzner + Cloudflare)

### Prerequisites
- Hetzner Cloud Server (CX21 or higher)
- Domain configured in Cloudflare
- API keys (Google Places, Anthropic)

### Setup

1. **Cloudflare DNS** - Add A records:
   | Name | Content |
   |------|---------|
   | scripe | YOUR_SERVER_IP |
   | api.scripe | YOUR_SERVER_IP |

2. **Cloudflare SSL** - Set to "Full" mode

3. **Server Setup**:
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone and configure
git clone https://github.com/YOUR_USER/scripe-standalone.git
cd scripe-standalone
cp .env.example .env
nano .env  # Add your API keys

# Start production
docker compose -f docker-compose.prod.yml up -d --build
```

## API Usage

### Authentication
```bash
# Login
curl -X POST https://api.scripe.fabioprivato.org/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

### Search
```bash
# Interpret query
curl -X POST https://api.scripe.fabioprivato.org/api/v1/ai/interpret \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Zahnärzte in Deutschland, Österreich, Schweiz"}'
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| GOOGLE_PLACES_API_KEY | Google Places API key | Yes |
| ANTHROPIC_API_KEY | Anthropic API key for AI | Yes |
| JWT_SECRET_KEY | JWT signing secret | Yes |
| DATABASE_URL | PostgreSQL connection URL | Yes |
| ALLOWED_ORIGINS | CORS allowed origins | Yes |

## License

Private - All rights reserved
