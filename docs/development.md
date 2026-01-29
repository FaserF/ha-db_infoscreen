# Development & Contributing 👩‍💻

Thank you for your interest in improving `ha-db_infoscreen`! This guide explains how to set up your environment, run tests, and contribute changes.

---

## 🛠️ Local Environment Setup

To get started with development, you'll need Python 3.12+ installed.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/FaserF/ha-db_infoscreen.git
    cd ha-db_infoscreen
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements_test.txt
    pip install -r custom_components/db_infoscreen/requirements.txt
    ```

---

## 🧪 Testing

We value stability. All Pull Requests must pass our automated test suite.

### Running Tests
We use `pytest` for all tests.
```bash
pytest
```

### Key Test Suites
-   **`tests/test_config_flow.py`**: Verifies the setup wizard and options menu.
-   **`tests/test_stability.py`**: Ensures the integration handles API errors and malformed data gracefully.
-   **`tests/test_translations.py`**: Checks for consistency across all language files.

---

## 🤖 CI/CD & Renovate

We use GitHub Actions to automate our quality control and deployment.

### Automated API Validation
Our `backend-api-update.yml` workflow is a unique "early warning system".
1.  **Renovate** monitors the [db-fakedisplay](https://github.com/derf/db-fakedisplay) project.
2.  When a new backend version is released, Renovate opens a PR updating our `.backend_version`.
3.  The CI automatically runs our stability tests against this new version.
4.  If it passes, we know the integration is safe to use with the new backend.

### Documentation Deployment
The documentation (this site!) is automatically built and deployed to GitHub Pages whenever changes are pushed to `main`.

---

## 🌍 Translations

Help us reach more users by contributing translations!

1.  Add your language code to `custom_components/db_infoscreen/translations/` (e.g., `fr.json`).
2.  Use `en.json` or `de.json` as a template.
3.  Run `pytest tests/test_translations.py` to ensure all keys are present.

---

## 📜 Pull Request Guidelines

1.  **Issue First**: For major changes, please open an issue first to discuss your proposal.
2.  **Formatting**: We use `black` for code formatting and `ruff` for linting.
3.  **Documentation**: If you add a new feature, please update the relevant `.md` file in the `docs/` folder.
