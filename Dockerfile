FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data/uploads data/exports xlsbase

# Expose port
EXPOSE 5000

# Volume for persistent data (database, uploads, excel files)
VOLUME ["/app/data", "/app/xlsbase"]

# Initialize DB and run with gunicorn
CMD ["sh", "-c", "python -c 'from database import init_db; init_db()' && gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 'app:create_app()'"]
