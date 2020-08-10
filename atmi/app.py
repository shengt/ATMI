
'''
export FLASK_APP=app.py
flask run
'''
from atmi import app

if __name__ == "__main__":
    # app.run(extra_files=[app.config["WEBPACK_MANIFEST_PATH"]], debug=True)
    app.run(host='0.0.0.0', port=9000, extra_files=[app.config["WEBPACK_MANIFEST_PATH"]])
