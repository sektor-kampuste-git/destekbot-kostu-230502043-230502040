FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV VERITABANI_YOLU=/tmp/destekbot.sqlite
EXPOSE 8000
# Render/Azure PORT değişkenini verir; yerelde 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
