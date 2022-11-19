from flask import Flask
from flask import render_template
from flask_session import Session
from flask import session
from flask import redirect
from flask import request
from mysql.connector import connection 
import json
import numpy as np 
import cv2
from keras.preprocessing import image
from tensorflow.keras.utils import load_img, img_to_array
from tensorflow.keras.models import load_model

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

fruit_model = load_model('../flask/fruit.h5')

database_details = {
    'user' : 'root',
    'host'     : 'localhost',
    'database' : 'ibm'
}

predict_result_fruit = {
    0 : 101,
    1 : False,
    2 : False,
    3 : 102,
    4 : 103,
    5 : False
}


predict_result_veg = {
    0 : 104,
    1 : False,
    2 : 105,
    3 : False,
    4 : 106,
    5 : 107,
    6 : 108,
    7 : 109,
    8 : 110
}

connectionObj = connection.MySQLConnection(**database_details)


@app.route("/login", methods=["POST"])
def login():
    if not session.get("name"):
        data = request.json;
        username = data["username"]
        password = data["password"]
        cursor = connectionObj.cursor(prepared=True)
        cursor.execute('''select * from user where username=%s and password=%s limit 1 ''', (username, password))
        result = list(cursor)
        cursor.close()
        if len(result) == 0:
            result = {}
            result['code'] = 403
            result['msg']  = 'access denied'
            return json.dumps(result)
        else:
            result = {}
            session["name"] = username
            session["type"] = "user"
            result['code'] = 200
            result['msg']  = 'login successfull'
            return json.dumps(result)
    else:
        return redirect("/")

@app.route("/")
def main():
    if not session.get("name"):
        return render_template("index.html")
    return render_template("main.html")

@app.route("/register", methods=["POST"])
def register():
    if not session.get("name"):
        try:
            data = request.json;
            username = data["username"]
            password = data["password"]
            mailId   = data["mail"]
            cursor = connectionObj.cursor(prepared=True)
            query  = '''insert into user(username, mailid, password) values(%s, %s, %s)'''
            cursor.execute(query, (username, mailId, password))
            connectionObj.commit()
            result = {'code':200, 'msg':'registered successfully'}
            return json.dumps(result)
        except:
            return json.dumps({'code':'500', 'msg':'register failed'})
    else:

        return redirect("/")


@app.route("/getdashboard")
def dashboard():
    import os
    os.system('pwd')
    with open("./static/img/image-dataset.json", 'r') as f:
        data = f.read()
    return data

def recommandation_data(hint_id):
    cursor = connectionObj.cursor(prepared=True)
    cursor.execute('''select symptoms, caused, org_control, chy_control from disease_description where id=%s''', (hint_id, ))
    (symptoms, caused, org_control, chy_control ) = list(cursor)[0]
    cursor.close()

    cursor = connectionObj.cursor(prepared=True)
    cursor.execute('''select name, link  from fertilizer where id=%s''', (hint_id, ))
    data = list(cursor)
    cursor.close()

    return (data, symptoms.decode(), caused.decode(), org_control.decode(), chy_control.decode())

@app.route("/recommandation" , methods=[ "POST"])
def recommandation():
    if session.get("name"):
        hint_id = request.json['hintId'];
        (data, symptoms, caused, org_control, chy_control ) = recommandation_data(hint_id)

        return render_template("recomandation.html", 
            fertilizer_data=data,
            sym=symptoms,
            cause=caused,
            org=org_control,
            chy=chy_control
        )
    else:
        return redirect("/404")

@app.route("/logout")
def logout():
    session.clear()
    return "logout"

@app.route("/upload" , methods=[ "POST"])
def upload():
    if session.get("name"):
        f = request.files['file']
        file_bytes = np.fromstring(f.read(), np.uint8)
        image_data = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
        img = cv2.resize(image_data, (128, 128))
        x = img_to_array(img)
        x = np.expand_dims(x, axis=0)
        predict_x=fruit_model.predict(x) 
        classes_x=np.argmax(predict_x,axis=1)
        predicted_result = predict_result_fruit[classes_x[0]]
        if predicted_result:
            (data, symptoms, caused, org_control, chy_control ) = recommandation_data(predicted_result)
        else:
            (data, symptoms, caused, org_control, chy_control ) = ("", "Healthy", "", "", "")
        return render_template("recomandation.html", 
            fertilizer_data=data,
            sym=symptoms,
            cause=caused,
            org=org_control,
            chy=chy_control
        )
    else:
        return redirect("/404")


if __name__ == '__main__':
    app.run(debug=True, port=1234)
