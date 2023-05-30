from pydantic import BaseModel, Field

class UserLoginSchema(BaseModel):
    username : str = Field(default = None)
    password : str = Field(default = None)
    class Config:
        the_schema = {
            "user_demo": {
                "email":"example",
                "password":"123"

            }

        }

class UserRegisterSchema(BaseModel):
    username : str = Field(default = None)
    password : str = Field(default = None)
    nama : str = Field(default = None)
    class Config:
        the_schema = {
            "user_demo": {
                "username":"example",
                "password":"123",
                "nama": "example"
            }
        }
