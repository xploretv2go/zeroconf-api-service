from service_discovery import app
import os
from dotenv import load_dotenv

load_dotenv()

app.run(host=os.getenv('HOST'), port=os.getenv('PORT'), debug=os.getenv('DEBUG'))