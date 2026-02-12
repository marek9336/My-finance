FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /app/app
COPY backend/ui /app/ui
COPY backend/scripts /app/scripts
COPY backend/start.sh /app/start.sh
COPY i18n /app/i18n
COPY db /db
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
