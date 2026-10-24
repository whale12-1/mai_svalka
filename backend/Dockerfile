FROM python:3.12-slim
WORKDIR /app

# 1. Устанавливаем CPU-версию PyTorch (вместо тяжелой CUDA-версии)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Копируем pyproject.toml и ставим остальные зависимости
COPY pyproject.toml .
RUN pip install --no-cache-dir -e . || pip install --no-cache-dir $(python -c "import tomllib;print(' '.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))")

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]