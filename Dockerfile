# ---------- Build React ----------
FROM node:20 AS frontend

WORKDIR /frontend

COPY frontend/package*.json ./

RUN npm install

COPY frontend/ .

RUN npm run build


# ---------- Python ----------
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy React build
COPY --from=frontend /frontend/dist ./static

EXPOSE 8000

CMD ["python", "app.py"]