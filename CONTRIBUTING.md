# 🧑‍💻 Contributing to Python Financial Analyst

Thanks for considering contributing to **Python Financial Analyst**!
We aim to build high-quality, maintainable tools for financial data analysis using Python.

To keep the codebase clean, consistent, and error-free, we use [Poetry](https://python-poetry.org/) for dependency management and [pre-commit](https://pre-commit.com/) for automated code checks.

---

## 📦 1. Clone and Install Dependencies

```bash
git clone https://github.com/Python-Financial-Analyst/pyfian.git
cd pyfian
poetry install
```

---

## ✅ 2. Set Up Pre-commit Hooks

```bash
poetry run pre-commit install
```

This installs Git hooks that automatically check your code **before every commit**.

You can also run all hooks manually:

```bash
poetry run pre-commit run --all-files
```

---

## 💡 3. Coding Guidelines

We use the following tools to enforce code quality:

| Tool         | Purpose                         |
|--------------|---------------------------------|
| `black`      | Code formatting                 |
| `isort`      | Import sorting                  |
| `flake8`     | Style and linting               |
| `mypy`       | Static type checking            |
| `pyupgrade`  | Upgrade to modern Python syntax |
| `detect-secrets` | Prevent secret leaks       |

Other guidelines:

- Write clean, type-annotated, well-documented code
- Use docstrings and meaningful variable names
- Follow the structure of existing modules and tests

---

## 🚀 4. Make Your Changes

Create a new branch:

```bash
git checkout -b feature/my-awesome-feature
```

Then make your changes, stage them, and commit:

```bash
git add .
git commit -m "Add feature: my awesome feature"
```

⚠️ The pre-commit hooks will run automatically before the commit is finalized.

---

## 🔁 5. Submit a Pull Request

Push your branch to GitHub and open a PR:

```bash
git push origin feature/my-awesome-feature
```

Go to: [https://github.com/Python-Financial-Analyst/pyfian](https://github.com/Python-Financial-Analyst/pyfian)
Create a Pull Request with a clear description of what you changed.

Make sure:

- Your PR passes all pre-commit hooks
- Code is tested and documented if necessary
- You follow the existing style and structure

---

## 🧪 Optional: Run Tests

We use `pytest` for testing:

```bash
poetry run pytest
```

---

## 🙏 Thanks!

Your contribution makes Python Financial Analyst better for everyone.
Feel free to open an issue or discussion if you have questions or ideas!
