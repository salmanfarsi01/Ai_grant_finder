import jwt
import datetime
import time

tkn = jwt.encode({
	'name': 'roni',
	'exp': datetime.datetime.now(datetime.UTC)+datetime.timedelta(seconds=5)
	}, 'abc', algorithm='HS256'
)

time.sleep(9)
try:
	print(jwt.decode(tkn, 'abc', algorithms=['HS256']))

except jwt.ExpiredSignatureError as e:
	print("error ..")