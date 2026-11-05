FROM python:3.12-slim
WORKDIR /app
COPY tsetmc_gateway ./tsetmc_gateway
ENV TSETMC_HOST=0.0.0.0 TSETMC_PORT=8080
EXPOSE 8080
CMD ["python", "-m", "tsetmc_gateway"]
