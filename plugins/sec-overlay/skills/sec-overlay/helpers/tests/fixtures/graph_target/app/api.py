from app.db import run_query
from typing import Any

def handler(request):
    user_input = request.args.get("q")
    return run_query(user_input)

app: Any = None  # stub: this fixture is scanned structurally, never imported/executed
@app.route('/widgets/<id>')
def get_widget(id):
    return run_query(id)
