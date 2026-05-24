FROM python:3.14-slim

WORKDIR /app

COPY pc/src/requirements-api.txt /tmp/requirements-api.txt
RUN pip install --no-cache-dir -r /tmp/requirements-api.txt

# Source and static files are bind-mounted via compose for dev (so --reload works).
# For a self-contained prod image, uncomment:
# COPY pc /app/pc

EXPOSE 8001

CMD ["python", "pc/src/api.py"]
