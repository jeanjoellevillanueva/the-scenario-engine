# the-scenario-engine
Enables educators to create interactive learning scenarios powered by large language models. A learner enters a simulated situation, interacts with an LLM-driven character, and is assessed against learning objectives. This is all without the educator needing to script every possible conversation path.

## Quick Start

```bash
# 1. Create and activate virtual environment
python3 -m venv env
source env/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and other settings

# 4. Run migrations
python manage.py migrate

# 5. Seed the test scenario
python manage.py seed_scenarios

# 6. Create a superuser (optional, for admin access)
python manage.py createsuperuser

# 7. Run the server
python manage.py runserver

# 8. Run tests
pytest
```