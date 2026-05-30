FROM python:3.14-slim

WORKDIR /app

# 1. Install uv using pip
RUN pip install uv

# 2. Copy your dependency files
COPY pyproject.toml uv.lock ./

COPY . .

# 3. Now uv sync will work perfectly!
RUN uv sync --frozen


CMD ["uv", "run", "news.py"]