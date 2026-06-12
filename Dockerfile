FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE $PORT

CMD streamlit run dashboard.py --server.port=${PORT:-8501} --server.address=0.0.0.0
