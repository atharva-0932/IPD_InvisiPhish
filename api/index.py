from api.__init__ import create_app
from flask import send_from_directory

app = create_app()

@app.route('/')
def index():
    return send_from_directory('../frontend/phish-guard-lite/dist', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend/phish-guard-lite/dist', path)

if __name__ == '__main__':
    app.run(debug=True)
