from fastapi import FastAPI, File, Body, UploadFile, Depends
from fastapi.responses import JSONResponse
from PIL import Image
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import numpy as np
import io
import jwt
import uvicorn
from db import mydb
from schemas import UserLoginSchema, UserRegisterSchema
from passlib.hash import bcrypt
from datetime import datetime
from jwt_handler import generate_token
from jwt_bearer import JWTBearer
from decouple import config

app = FastAPI()

model = tf.keras.models.load_model('./model/waste_CNN_model.h5')

mycursor = mydb.cursor()

@app.get("/")
def get_root():
    return {"message": "Hello World"}

@app.post("/user/login", tags=["user"])
def user_login(user: UserLoginSchema = Body(...)):
    
    username = user.username
    password = user.password

    if (username == None or password == None):
        data = {
            "status": False,
            "message": "USERNAME_PASSWORD_REQUIRED"
            }
        return JSONResponse(content=data, status_code=400)
    
    res = (username,)

    mycursor.execute("SELECT * FROM users WHERE username= %s", res)
    myresult = mycursor.fetchall()

    if (len(myresult) == 1):
        res_pass = myresult[0][2]
        res_username = myresult[0][1]
        res_nama = myresult[0][3]
        res_idUser = myresult[0][0]
        is_valid = bcrypt.verify(password, res_pass)
        if is_valid:
            data = {
                "status": True,
                "message": "USER_LOGIN_SUCCESS",
                "token": generate_token(res_idUser),
                "data": {
                    "username": res_username,
                    "nama": res_nama
                }
            }
            return JSONResponse(content=data, status_code=200)
        else:
            data = {
                "status": False,
                "message": "WRONG_PASSWORD"
            }
            return JSONResponse(content=data, status_code=400)
    else:
        data = {
            "status": False,
            "message": "USER_NOT_FOUND"
            }
        return JSONResponse(content=data, status_code=404)
    
@app.post("/user/register", tags=["user"])
def user_register(user: UserRegisterSchema = Body(...)):

    username = user.username
    password = user.password
    nama = user.nama
    created_at = datetime.now()
    updated_at = datetime.now()

    if (username == None or password == None or nama == None):
        data = {
            "status": False,
            "message": "USERNAME_PASSWORD_NAMA_REQUIRED"
            }
        return JSONResponse(content=data, status_code=400)

    res = (username,)
    mycursor.execute("SELECT * FROM users WHERE username= %s", res)
    myresult = mycursor.fetchall()

    if (len(myresult) == 0):
        sql = "INSERT INTO users (username, password, nama, createdAt, updatedAt) VALUES (%s, %s, %s, %s, %s)"
        val = (username, bcrypt.hash(password), nama, created_at, updated_at)
        mycursor.execute(sql, val)
        mydb.commit()
        data = {
            "status": True,
            "message": "USER_REGISTER_SUCCESS"
            }
        return JSONResponse(content=data, status_code=200)
    else:
        data = {
            "status": False,
            "message": "USERNAME_ALREADY_EXIST"
            }
        return JSONResponse(content=data, status_code=400)

@app.post("/predict", dependencies=[Depends(JWTBearer())], tags=["predict"])
async def predict(file: UploadFile = File(...)):

    contents = await file.read()
    img = Image.open(io.BytesIO(contents))
    img = img.resize((64, 64))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)

    result = model.predict(img_array)
    predicted_class = np.argmax(result)
    if result[0][0] == 1:
        prediction = 'Recyclable Waste'
    else:
        prediction = 'Organic Waste'

    data = {
            "status": True,
            "type": prediction,
            "probability": str(result[0][predicted_class])
            }
    return JSONResponse(content=data, status_code=200)