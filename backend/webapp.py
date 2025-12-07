# backend/webapp.py

from flask import Flask, render_template
from .routes_pdf import pdf_bp
from .routes_process import process_bp

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

# Register blueprints
app.register_blueprint(pdf_bp)
app.register_blueprint(process_bp)

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
