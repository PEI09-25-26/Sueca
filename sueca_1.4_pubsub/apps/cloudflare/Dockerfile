FROM cloudflare/cloudflared:latest

WORKDIR /etc/cloudflared

COPY apps/cloudflare/config.yml ./
COPY apps/cloudflare/9282ae9d-2ebc-4626-a8c3-a1e4e7801886.json ./
COPY apps/cloudflare/cert.pem ./

CMD ["tunnel", "--config", "./config.yml", "run", "sueca-api"]
