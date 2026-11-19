# Build frontend
FROM node:22-slim AS fe
WORKDIR /fe
COPY app/frontend/package*.json ./
RUN npm ci
COPY app/frontend/ ./
RUN npm run build

# Backend + frontend statis
FROM python:3.12-slim
WORKDIR /srv
COPY app/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/backend/app ./app
COPY --from=fe /fe/dist ./static
# Kit (data/, templates/) dipasang sebagai volume read-only di /kit
ENV INAPROC_KIT_DIR=/kit INAPROC_STORAGE_DIR=/storage
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
