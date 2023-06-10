from fastapi import FastAPI, File, Body, UploadFile, Depends
from fastapi.responses import JSONResponse
from google.cloud import storage
from PIL import Image
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import numpy as np
import io
import jwt
import uvicorn
import imghdr
from db import mydb
from schemas import UserLoginSchema, UserRegisterSchema
from passlib.hash import bcrypt
from datetime import datetime
from jwt_handler import generate_token
from jwt_bearer import JWTBearer
from decouple import config

app = FastAPI()

service_account_info = {
    "type": config("TYPE"),
    "project_id": config("PROJECT_ID"),
    "private_key_id": config("PRIVATE_KEY_ID"),
    "private_key": config("PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": config("CLIENT_EMAIL"),
    "client_id": config("CLIENT_ID"),
    "auth_uri": config("AUTH_URI"),
    "token_uri": config("TOKEN_URI"),
    "auth_provider_x509_cert_url": config("AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": config("CLIENT_X509_CERT_URL"),
    "universe_domain": config("UNIVERSE_DOMAIN")
}

model = tf.keras.models.load_model('model/waste_CNN_model.h5')

bucket_name = config("BUCKET_NAME")

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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
                    "idUser": res_idUser,
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
async def predict(user_id: str, file: UploadFile = File(...)):
    try:
        file_extension = imghdr.what(None, h=file.file.read(32))
        file.file.seek(0)

        if not file_extension or file_extension not in ALLOWED_EXTENSIONS:
            return JSONResponse(content={"status": False, "message": "File type not allowed."}, status_code=400)
        
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return JSONResponse(content={"status": False, "message": "File size exceeds the maximum limit."}, status_code=400)
        
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
                "probability": str(result[0][predicted_class]),
                "user_id": user_id
                }

        client = storage.Client.from_service_account_info(service_account_info)
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(file.filename)
        file.file.seek(0)

        blob.upload_from_file(file.file)

        sql = "INSERT INTO predict_history (user_id, type, probability, image_url) VALUES (%s, %s, %s, %s)"
        val = (user_id, prediction, str(result[0][predicted_class]), f"https://storage.googleapis.com/{bucket_name}/{file.filename}")
        mycursor.execute(sql, val)
        mydb.commit()
        
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        return JSONResponse(content={"status": False, "message": str(e)}, status_code=500)