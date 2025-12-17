# Stage 1.7: HTTPS with Caddy - COMPLETED ✅

## Overview

**Goal**: Add automatic HTTPS/SSL to the application using Caddy reverse proxy.

**Estimated Time**: ~30 minutes

**Deliverable**: Secure HTTPS access at `https://openmsk.com` with automatic certificate management.

---

## Prerequisites

- ✅ Stage 1.6 complete (Docker deployment working)
- ✅ Domain pointing to server (DNS A record configured)
- ✅ Ports 80 and 443 accessible (firewall rules)

---

## How Caddy Works

Caddy is a modern web server that:

1. **Automatically obtains SSL certificates** from Let's Encrypt (free)
2. **Automatically renews certificates** before expiry (every 90 days)
3. **Acts as reverse proxy** - forwards requests to your FastAPI app

```
User Request Flow:
┌──────────┐      ┌─────────────────┐      ┌─────────────┐
│  Browser │ ──── │ Caddy (443/80)  │ ──── │ FastAPI     │
│          │ HTTPS│ Auto SSL        │ HTTP │ (8000)      │
└──────────┘      └─────────────────┘      └─────────────┘
```

---

## Task Summary

| Task | Type | Description |
|------|------|-------------|
| 1.7.1 | AI Agent | Create `docker/Caddyfile` |
| 1.7.2 | AI Agent | Update `docker/docker-compose.yml` |
| 1.7.3 | **HUMAN** | Add GCP firewall rules for ports 80/443 |
| 1.7.4 | Mixed | Deploy and verify HTTPS |

---

## 1.7.1: Caddyfile Configuration

**File**: `docker/Caddyfile`

```
# Main domain - reverse proxy to FastAPI
openmsk.com {
    reverse_proxy web:8000
}

# WWW redirect to non-www
www.openmsk.com {
    redir https://openmsk.com{uri} permanent
}
```

**What this does:**
- `openmsk.com` → Proxies to FastAPI container on port 8000
- `www.openmsk.com` → Redirects to `https://openmsk.com`
- SSL certificates obtained automatically on first request

---

## 1.7.2: Docker Compose with Caddy

**File**: `docker/docker-compose.yml`

Key changes:
- Added `caddy` service with ports 80 and 443
- Changed `web` and `redis` from `ports` to `expose` (internal only)
- Added `caddy_data` and `caddy_config` volumes for certificate storage

### Services Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                                                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌───────┐ │
│  │  Caddy  │───▶│   Web   │───▶│  Redis  │◀───│Worker │ │
│  │ :80/:443│    │  :8000  │    │  :6379  │    │       │ │
│  └─────────┘    └─────────┘    └─────────┘    └───────┘ │
│       ▲                                                  │
└───────│──────────────────────────────────────────────────┘
        │
   Internet (HTTPS only)
```

### Volume Persistence

| Volume | Purpose |
|--------|---------|
| `caddy_data` | SSL certificates (survives container rebuilds) |
| `caddy_config` | Caddy configuration cache |
| `redis_data` | Redis persistence |
| `app_data` | Application data (uploads, results) |

---

## 1.7.3: GCP Firewall Rules (HUMAN TASK)

> ⚠️ **This must be done by a human in the GCP Console**

### Create HTTP Rule (Port 80)

1. GCP Console → **VPC network** → **Firewall**
2. Click **CREATE FIREWALL RULE**
3. Configure:

| Field | Value |
|-------|-------|
| Name | `allow-http` |
| Network | `default` |
| Priority | `1000` |
| Direction | Ingress |
| Action | Allow |
| Targets | Specified target tags |
| Target tags | `knee-pipeline` |
| Source IPv4 ranges | `0.0.0.0/0` |
| Protocols/ports | TCP: `80` |

### Create HTTPS Rule (Port 443)

1. Click **CREATE FIREWALL RULE** again
2. Configure:

| Field | Value |
|-------|-------|
| Name | `allow-https` |
| Network | `default` |
| Priority | `1000` |
| Direction | Ingress |
| Action | Allow |
| Targets | Specified target tags |
| Target tags | `knee-pipeline` |
| Source IPv4 ranges | `0.0.0.0/0` |
| Protocols/ports | TCP: `443` |

### Verify VM Has Network Tag

Ensure your VM has the `knee-pipeline` network tag (should already be set from Stage 1.6).

---

## 1.7.4: Deploy and Verify

### Deploy

```bash
cd ~/programming/kneepipeline_segmentaton_website/docker

# Pull latest code (if needed)
git pull

# Rebuild and restart
docker compose down
docker compose up -d --build

# Check status
docker compose ps
```

**Expected output:**
```
NAME                    STATUS    PORTS
knee-pipeline-caddy     running   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
knee-pipeline-redis     running   6379/tcp
knee-pipeline-web       running   8000/tcp
knee-pipeline-worker    running
```

### Verify HTTPS

```bash
# Check Caddy logs (watch for certificate provisioning)
docker compose logs -f caddy

# Test HTTPS
curl -I https://openmsk.com
```

### Test in Browser

Navigate to: `https://openmsk.com`

- ✅ Should show padlock icon (secure connection)
- ✅ Should load the Knee MRI Analysis Pipeline
- ✅ `http://openmsk.com` should redirect to `https://`
- ✅ `www.openmsk.com` should redirect to `https://openmsk.com`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Certificate not provisioning | Check domain DNS points to server IP |
| Connection refused on 443 | Verify GCP firewall rule for port 443 |
| Caddy container keeps restarting | Check `docker compose logs caddy` |
| "Too many redirects" | Clear browser cache, check Caddyfile syntax |

### View Caddy Logs

```bash
docker compose logs -f caddy
```

Look for:
- `certificate obtained successfully` - Good!
- `failed to obtain certificate` - DNS or firewall issue

### Manual Certificate Test

```bash
# Check if Let's Encrypt can reach your domain
curl -I http://openmsk.com/.well-known/acme-challenge/test
```

---

## Server Migration Checklist

When moving to a new server (e.g., GPU VM):

```
□ Spin up new VM
□ Add network tag 'knee-pipeline'
□ Clone repo
□ cp docker/.env.example docker/.env
□ docker compose up -d --build
□ Update GoDaddy A record to new IP
□ Wait ~10 min for DNS propagation
□ Caddy auto-provisions new certificates
□ Verify https://openmsk.com works
```

**Note**: Certificates are NOT transferred between servers. Caddy gets new certificates automatically on each new server.

---

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `docker/Caddyfile` | CREATE | Caddy configuration |
| `docker/docker-compose.yml` | MODIFY | Added Caddy service |

---

## Security Notes

1. **Ports 80/443 only**: Redis and FastAPI are NOT directly exposed to internet
2. **Automatic HTTPS redirect**: HTTP requests redirect to HTTPS
3. **Certificate auto-renewal**: Caddy handles this automatically
4. **No manual certificate management**: Let's Encrypt handles everything

---

## Success Criteria

- [ ] Caddy container running
- [ ] `https://openmsk.com` shows padlock icon
- [ ] `http://openmsk.com` redirects to HTTPS
- [ ] `www.openmsk.com` redirects to `openmsk.com`
- [ ] Upload → Process → Download works over HTTPS

---

## Date Completed

December 17, 2025 ✅
