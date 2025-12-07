from flask import Flask, render_template, request
from backend.routes_pdf import pdf_bp
from backend.routes_process import process_bp

def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    # API routes
    app.register_blueprint(pdf_bp, url_prefix="/api")
    app.register_blueprint(process_bp, url_prefix="/")

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
