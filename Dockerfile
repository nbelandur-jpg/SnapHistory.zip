FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Render expects web services to listen on $PORT (defaults to 10000)
ENV PORT=10000
EXPOSE 10000

CMD ["bash", "-lc", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

