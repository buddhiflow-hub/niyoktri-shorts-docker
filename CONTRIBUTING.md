# Contributing to Niyoktri Shorts Factory

Thank you for your interest in contributing to **Niyoktri Shorts Factory**! We welcome community contributions, bug reports, feature requests, and improvements.

---

## 🛠️ Development Workflow

### 1. Fork and Clone
1. Fork the repository on GitHub to your account.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/niyoktri-shorts-docker.git
   cd niyoktri-shorts-docker
   ```

### 2. Configure Environment
Create your `.env` file from `.env.example`:
```bash
cp .env.example .env
```
*(Add test API keys for Pexels / Pixabay if testing live stock footage retrieval).*

### 3. Testing with Docker
You do not need local Python or CUDA configurations if using Docker:
```bash
# Build the container
docker compose build

# Run unit / smoke tests
docker compose run --rm shorts-factory python src/main.py --mode test
```

### 4. Testing Locally (Without Docker)
If you prefer developing directly on your host machine:
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run syntax check
python -m py_compile src/main.py src/**/*.py

# Run test render
python src/main.py --mode test
```

---

## 📋 Pull Request Guidelines

1. **Create a descriptive branch**:
   ```bash
   git checkout -b feature/awesome-new-transition
   ```
2. **Commit with clean conventional commit messages**:
   - `feat: add TikTok publisher integration`
   - `fix: handle edge case in Pexels portrait aspect ratio`
   - `docs: update setup steps for Windows WSL`
3. **Ensure tests pass**:
   - Make sure `python -m py_compile` passes without errors.
   - Run a test render.
4. **Submit your Pull Request** targeting the `main` branch.

---

## 💬 Community & Questions
For issues, questions, or ideas:
- Open an Issue on GitHub
- Contact maintainer: [buddhiflow@gmail.com](mailto:buddhiflow@gmail.com)
