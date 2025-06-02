FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

RUN mkdir media static data

COPY data/ingredients.json data/
COPY . .

RUN chmod +x start.sh

CMD ["./start.sh"]