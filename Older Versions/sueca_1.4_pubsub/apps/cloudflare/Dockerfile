FROM cloudflare/cloudflared:latest

WORKDIR /etc/cloudflared

COPY --chmod=644 apps/cloudflare/config.yml ./
COPY --chmod=644 apps/cloudflare/63686722-dd80-4dc9-b05b-cebe1d9c6d0c.json ./
COPY --chmod=644 apps/cloudflare/cert.pem ./

CMD ["tunnel", "--config", "./config.yml", "run", "sueca-api"]
