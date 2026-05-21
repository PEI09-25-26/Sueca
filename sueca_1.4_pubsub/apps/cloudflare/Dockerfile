FROM cloudflare/cloudflared:latest

WORKDIR /etc/cloudflared

COPY --chmod=644 apps/cloudflare/config.yml ./
COPY --chmod=644 apps/cloudflare/9282ae9d-2ebc-4626-a8c3-a1e4e7801886.json ./
COPY --chmod=644 apps/cloudflare/cert.pem ./

CMD ["tunnel", "--config", "./config.yml", "run", "sueca-api"]
