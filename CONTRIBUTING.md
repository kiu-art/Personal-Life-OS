# Contributing to Personal Life OS

Thank you for contributing to Personal Life OS. This guide outlines how to set up the project locally, adhere to code standards, and submit pull requests.

---

## 1. Development Setup

### Prerequisites

* **Backend**: Python 3.9+, [Uvicorn](https://www.uvicorn.org/), optional local MongoDB (runs in-memory mock if omitted)
* **Mobile**: Flutter 3.24+, Android SDK 34 (minSdk 23), Android emulator or physical device

### Backend Setup

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Mobile Setup

```bash
cd mobile
flutter pub get
flutter run
```

> **Note**: Ambient microphone capture and notification listening services require granting runtime permissions on an Android device or emulator.

---

## 2. Development Workflow

1. Create a descriptive branch from `main`:
   ```bash
   git checkout -b feature/<feature-name>
   # or
   git checkout -b fix/<bug-name>
   ```
2. Keep branches focused on a single concern or feature.
3. Test your changes locally before submitting.

---

## 3. Testing and Code Quality

Run tests and static analysis for any components you touch:

### Mobile

```bash
cd mobile
flutter analyze
flutter test
```

All analysis checks must pass with zero issues and existing tests in `test/` must pass.

### Backend

```bash
cd backend
python3 -m pytest -q
```

Include corresponding test coverage in `backend/` for new endpoints or business logic changes.

---

## 4. Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

* `feat:` A new feature
* `fix:` A bug fix
* `refactor:` Code restructuring without behavioral changes
* `test:` Adding or updating tests
* `docs:` Documentation changes
* `chore:` Tooling, dependency, or configuration changes

**Format:**
```
<type>(<scope>): <short description>
```

**Examples:**
* `feat(mobile): add whisper model download progress indicator`
* `fix(backend): correct timezone offset calculation in schedule shift`

---

## 5. Submitting a Pull Request

1. Push your branch to GitHub.
2. Open a Pull Request targeting `main`.
3. Fill out the PR description with:
   * **Summary**: Concise overview of the changes.
   * **Motivation**: Context or linked issue (`Closes #<issue>`).
   * **Verification**: How the changes were tested (commands run and results).
4. Verify that no secrets (`.env`, credentials, keystores) or build artifacts (`build/`, `.dart_tool/`, `__pycache__/`) are included in your commit.
