from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/api/status")
def status():
    return jsonify(
        {
            "application": "The Foreman",
            "company": "HardHead Works",
            "status": "online",
            "version": "0.4.0",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
